"""
Streaming de données en temps réel depuis Binance WebSocket.
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any
from pymongo.database import Database
import websocket

from .config import SETTINGS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("STREAM_DATA")


class BinanceStreamClient:
    """Client pour streamer les données en temps réel depuis Binance."""

    def __init__(self, symbols: List[str], db: Optional[Database] = None,
                 callback: Optional[Callable] = None):
        """
        Initialise le client de streaming.

        Args:
            symbols: Liste des symboles à streamer (ex: ['btcusdt', 'ethusdt'])
            db: Base de données MongoDB pour stocker les données (optionnel)
            callback: Fonction callback appelée pour chaque message reçu (optionnel)
        """
        self.symbols = [s.lower() for s in symbols]
        self.db = db
        self.callback = callback
        self.ws = None
        self.ws_url = self._build_url()
        self.running = False
        self.thread = None
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10

    def _build_url(self) -> str:
        """Construit l'URL WebSocket pour les symboles."""
        base_url = SETTINGS["URL_STREAM"]
        # Format: wss://stream.binance.com:9443/ws/btcusdt@trade/ethusdt@trade
        streams = "/".join([f"{symbol}@trade" for symbol in self.symbols])
        return f"{base_url}/{streams}"

    def _on_message(self, ws, message):
        """Callback appelé quand un message est reçu."""
        try:
            data = json.loads(message)

            # Parse les données du trade
            parsed_data = {
                "symbol": data.get("s"),
                "price": float(data.get("p", 0)),
                "quantity": float(data.get("q", 0)),
                "timestamp": datetime.fromtimestamp(data.get("T", 0) / 1000),
                "trade_id": data.get("t"),
                "is_buyer_maker": data.get("m", False),
            }

            logger.debug(f"Received trade: {parsed_data['symbol']} @ {parsed_data['price']}")

            # Store dans MongoDB si disponible
            if self.db is not None:
                self._store_trade(parsed_data)

            # Appel du callback si fourni
            if self.callback is not None:
                self.callback(parsed_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        """Callback appelé en cas d'erreur."""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Callback appelé quand la connexion est fermée."""
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")

        # Tentative de reconnexion si le client est toujours en cours d'exécution
        if self.running:
            logger.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            if self.running:
                self._connect()

    def _on_open(self, ws):
        """Callback appelé quand la connexion est ouverte."""
        logger.info(f"WebSocket connected to {self.ws_url}")
        logger.info(f"Streaming data for symbols: {', '.join(self.symbols)}")

    def _store_trade(self, trade_data: Dict[str, Any]):
        """
        Store un trade dans MongoDB.

        Args:
            trade_data: Données du trade à stocker
        """
        try:
            collection_name = SETTINGS["MONGO_COLLECTION_STREAMING"]
            collection = self.db[collection_name]
            collection.insert_one(trade_data)
        except Exception as e:
            logger.error(f"Error storing trade in MongoDB: {e}")

    def _connect(self):
        """Établit la connexion WebSocket."""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            if self.running:
                time.sleep(self.reconnect_delay)
                self._connect()

    def start(self):
        """Démarre le streaming dans un thread séparé."""
        if self.running:
            logger.warning("Stream is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._connect, daemon=True)
        self.thread.start()
        logger.info("Stream started in background thread")

    def stop(self):
        """Arrête le streaming."""
        if not self.running:
            logger.warning("Stream is not running")
            return

        self.running = False
        if self.ws:
            self.ws.close()

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("Stream stopped")

    def stream_for_duration(self, duration_seconds: int):
        """
        Stream les données pendant une durée déterminée.

        Args:
            duration_seconds: Durée en secondes
        """
        logger.info(f"Starting stream for {duration_seconds} seconds...")
        self.start()

        try:
            time.sleep(duration_seconds)
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
        finally:
            self.stop()


def stream_trades(symbols: List[str], duration_seconds: Optional[int] = None,
                  db: Optional[Database] = None,
                  callback: Optional[Callable] = None) -> BinanceStreamClient:
    """
    Fonction helper pour streamer les trades.

    Args:
        symbols: Liste des symboles à streamer
        duration_seconds: Durée du stream (None = infini)
        db: Base de données MongoDB (optionnel)
        callback: Fonction callback pour chaque trade (optionnel)

    Returns:
        BinanceStreamClient: Instance du client

    Example:
        >>> def on_trade(data):
        ...     print(f"{data['symbol']}: {data['price']}")
        >>> client = stream_trades(['BTCUSDT'], duration_seconds=10, callback=on_trade)
    """
    client = BinanceStreamClient(symbols=symbols, db=db, callback=callback)

    if duration_seconds:
        client.stream_for_duration(duration_seconds)
    else:
        client.start()
        try:
            # Garde le stream actif indéfiniment
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping stream...")
            client.stop()

    return client


if __name__ == "__main__":
    # Test simple
    def print_trade(data):
        print(f"[{data['timestamp']}] {data['symbol']}: ${data['price']:.2f} (qty: {data['quantity']:.4f})")

    # Stream BTCUSDT pendant 30 secondes
    stream_trades(['BTCUSDT', 'ETHUSDT'], duration_seconds=30, callback=print_trade)

