"""
Tests pour le streaming de données en temps réel.
"""
import sys
import os
import time
import json
from datetime import datetime

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.stream_data import BinanceStreamClient, stream_trades


def test_stream_client_basic():
  """Test basique du client de streaming."""
  print("\n=== Test 1: Streaming basique ===")

  received_trades = []

  def collect_trade(data):
    received_trades.append(data)
    print(f"[{data['timestamp']}] {data['symbol']}: ${data['price']:.2f} (qty: {data['quantity']:.4f})")

  # Stream BTCUSDT pendant 10 secondes
  client = BinanceStreamClient(symbols=['BTCUSDT'], callback=collect_trade)
  client.stream_for_duration(10)

  print(f"\nReceived {len(received_trades)} trades in 10 seconds")

  if received_trades:
    first_trade = received_trades[0]
    print(f"First trade: {first_trade['symbol']} @ ${first_trade['price']:.2f}")

    last_trade = received_trades[-1]
    print(f"Last trade: {last_trade['symbol']} @ ${last_trade['price']:.2f}")

  assert len(received_trades) > 0, "Should have received at least one trade"


def test_multiple_symbols():
  """Test du streaming avec plusieurs symboles."""
  print("\n=== Test 2: Multiple symboles ===")

  trades_by_symbol = {}

  def categorize_trade(data):
    symbol = data['symbol']
    if symbol not in trades_by_symbol:
      trades_by_symbol[symbol] = []
    trades_by_symbol[symbol].append(data)
    print(f"[{symbol}] ${data['price']:.2f}")

  # Stream plusieurs cryptos
  symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
  client = BinanceStreamClient(symbols=symbols, callback=categorize_trade)
  client.stream_for_duration(15)

  print(f"\nTrades received per symbol:")
  for symbol, trades in trades_by_symbol.items():
    print(f"  - {symbol}: {len(trades)} trades")

  assert len(trades_by_symbol) > 0, "Should have received trades for at least one symbol"


def test_stream_helper_function():
  """Test de la fonction helper stream_trades."""
  print("\n=== Test 3: Helper function ===")

  trade_count = [0]  # Utiliser une liste pour pouvoir modifier dans le callback

  def count_trade(data):
    trade_count[0] += 1
    if trade_count[0] <= 5:  # Afficher seulement les 5 premiers
      print(f"Trade #{trade_count[0]}: {data['symbol']} @ ${data['price']:.2f}")

  # Utiliser la fonction helper
  stream_trades(['BTCUSDT'], duration_seconds=8, callback=count_trade)

  print(f"\nTotal trades: {trade_count[0]}")
  assert trade_count[0] > 0, "Should have received at least one trade"


def test_websocket_connection():
  """Test de connexion WebSocket (sans callback)."""
  print("\n=== Test 4: WebSocket connection test ===")

  connection_established = [False]

  def on_first_trade(data):
    connection_established[0] = True
    print(f"Connection established! First trade: {data['symbol']} @ ${data['price']:.2f}")

  client = BinanceStreamClient(symbols=['BTCUSDT'], callback=on_first_trade)
  client.start()

  # Attendre jusqu'à 10 secondes pour recevoir au moins un trade
  for i in range(10):
    if connection_established[0]:
      break
    time.sleep(1)

  client.stop()

  assert connection_established[0], "Should have established connection and received data"


def test_client_websocket_example():
  """
  Exemple de code client pour tester le WebSocket de l'API.
  Ce test nécessite que l'API soit en cours d'exécution.
  """
  print("\n=== Test 5: Client WebSocket Example ===")
  print("\nPour tester le WebSocket de l'API, exécutez ce code JavaScript dans un navigateur:")
  print("""
    // Connexion au WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/stream/BTCUSDT');
    
    ws.onopen = () => {
        console.log('Connected to stream');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(`${data.symbol}: $${data.price} at ${data.timestamp}`);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('Connection closed');
    };
    
    // Pour envoyer un ping
    ws.send('ping');
    """)

  print("\nOu utilisez Python avec websocket-client:")
  print("""
    import websocket
    import json
    
    def on_message(ws, message):
        data = json.loads(message)
        print(f"{data['symbol']}: ${data['price']}")
    
    ws = websocket.WebSocketApp(
        'ws://localhost:8000/ws/stream/BTCUSDT',
        on_message=on_message
    )
    ws.run_forever()
    """)


if __name__ == "__main__":
  print("=" * 60)
  print("TESTS DE STREAMING EN TEMPS RÉEL")
  print("=" * 60)

  try:
    # Exécuter tous les tests
    test_stream_client_basic()
    time.sleep(2)

    test_multiple_symbols()
    time.sleep(2)

    test_stream_helper_function()
    time.sleep(2)

    test_websocket_connection()
    time.sleep(2)

    test_client_websocket_example()

    print("\n" + "=" * 60)
    print("TOUS LES TESTS SONT PASSÉS!")
    print("=" * 60)

  except AssertionError as e:
    print(f"\nTest échoué: {e}")
    sys.exit(1)
  except KeyboardInterrupt:
    print("\n\nTests interrompus par l'utilisateur")
    sys.exit(0)
  except Exception as e:
    print(f"\nErreur inattendue: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
