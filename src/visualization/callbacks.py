"""
Callbacks pour le dashboard Dash
"""
import logging
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate
import requests

logger = logging.getLogger("CRYPTO_DASH_CALLBACKS")

# URL de l'API (peut être configurée via variable d'environnement pour Docker)
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')
logger.info(f"API URL configurée: {API_BASE_URL}")


def register_callbacks(app):
  """Enregistre tous les callbacks de l'application."""

  @app.callback(
    [Output('symbol-dropdown', 'options'),
     Output('interval-dropdown', 'options')],
    Input('refresh-button', 'n_clicks')
  )
  def load_metadata(n_clicks):
    """Charge les symboles et intervalles disponibles."""
    try:
      # Récupérer les symboles
      response = requests.get(f"{API_BASE_URL}/api/symbols")
      symbols_data = response.json()
      symbol_options = [
        {'label': f"{symbol} {'⭐' if symbol == 'BTCUSDT' else ''}", 'value': symbol}
        for symbol in symbols_data.get('symbols', [])[:50]  # Limiter à 50 pour la démo
      ]

      # Récupérer les intervalles
      response = requests.get(f"{API_BASE_URL}/api/intervals")
      intervals_data = response.json()
      interval_options = [
        {'label': interval, 'value': interval}
        for interval in intervals_data.get('intervals', [])
      ]

      return symbol_options, interval_options

    except Exception as e:
      logger.error(f"Erreur lors du chargement des métadonnées: {e}")
      return [], []

  @app.callback(
    [Output('historical-data-store', 'data'),
     Output('current-price', 'children'),
     Output('price-change', 'children'),
     Output('volume-24h', 'children'),
     Output('high-low', 'children')],
    [Input('refresh-button', 'n_clicks'),
     Input('auto-refresh-interval', 'n_intervals')],
    [State('symbol-dropdown', 'value'),
     State('interval-dropdown', 'value'),
     State('period-dropdown', 'value')]
  )
  def update_data(n_clicks, n_intervals, symbol, interval, days):
    """Met à jour les données historiques et les stats."""
    if not symbol or not interval:
      raise PreventUpdate

    # dbc.Select retourne des strings, convertir en int
    days = int(days) if days else 7

    try:
      # Calculer les dates
      end_date = datetime.now()
      start_date = end_date - timedelta(days=days)

      # Récupérer les données historiques
      # L'API attend start_time et end_time en format ISO, et le symbol dans l'URL
      params = {
        'interval': interval,
        'start_time': start_date.isoformat(),
        'end_time': end_date.isoformat(),
        'limit': 1000
      }

      response = requests.get(f"{API_BASE_URL}/api/historical/{symbol}", params=params)

      # L'API retourne directement une liste, pas un dict avec 'data'
      if response.status_code != 200:
        logger.error(f"API returned status {response.status_code}: {response.text}")
        return None, "N/A", "N/A", "N/A", "N/A"

      data = response.json()

      if not data or not isinstance(data, list):
        logger.warning(f"No data returned for {symbol}")
        return None, "N/A", "N/A", "N/A", "N/A"

      # Convertir en DataFrame
      df = pd.DataFrame(data)
      df['open_time'] = pd.to_datetime(df['open_time'])
      df = df.sort_values('open_time')

      # Calculer les stats
      latest = df.iloc[-1]
      previous = df.iloc[-2] if len(df) > 1 else latest

      current_price = f"${latest['close']:,.2f}"

      price_change = ((latest['close'] - previous['close']) / previous['close']) * 100
      price_change_str = f"{price_change:+.2f}%"

      volume_24h = f"${latest['volume']:,.0f}"

      high_24h = df['high'].max()
      low_24h = df['low'].min()
      high_low_str = f"${high_24h:,.2f} / ${low_24h:,.2f}"

      # Stocker les données pour les graphiques
      data_dict = df.to_dict('records')

      return data_dict, current_price, price_change_str, volume_24h, high_low_str

    except Exception as e:
      logger.error(f"Erreur lors de la mise à jour des données: {e}")
      return None, "Erreur", "Erreur", "Erreur", "Erreur"

  @app.callback(
    Output('price-chart', 'figure'),
    Input('historical-data-store', 'data')
  )
  def update_price_chart(data):
    """Met à jour le graphique des prix."""
    if not data:
      return create_empty_figure("Aucune donnée disponible")

    try:
      df = pd.DataFrame(data)
      df['open_time'] = pd.to_datetime(df['open_time'])

      # Créer le graphique en chandelier
      fig = go.Figure()

      fig.add_trace(go.Candlestick(
        x=df['open_time'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Prix',
        increasing_line_color='#00d4aa',
        decreasing_line_color='#ff4757'
      ))

      # Ajouter les moyennes mobiles
      df['ma7'] = df['close'].rolling(window=7).mean()
      df['ma30'] = df['close'].rolling(window=30).mean()

      fig.add_trace(go.Scatter(
        x=df['open_time'],
        y=df['ma7'],
        mode='lines',
        name='MA 7',
        line=dict(color='#ffa502', width=1.5)
      ))

      fig.add_trace(go.Scatter(
        x=df['open_time'],
        y=df['ma30'],
        mode='lines',
        name='MA 30',
        line=dict(color='#5f27cd', width=1.5)
      ))

      fig.update_layout(
        template='plotly_dark',
        xaxis_title='Date',
        yaxis_title='Prix (USD)',
        hovermode='x unified',
        showlegend=True,
        height=500,
        margin=dict(l=50, r=50, t=30, b=50)
      )

      fig.update_xaxes(rangeslider_visible=False)

      return fig

    except Exception as e:
      logger.error(f"Erreur lors de la création du graphique de prix: {e}")
      return create_empty_figure("Erreur lors du chargement")

  @app.callback(
    Output('volume-chart', 'figure'),
    Input('historical-data-store', 'data')
  )
  def update_volume_chart(data):
    """Met à jour le graphique des volumes."""
    if not data:
      return create_empty_figure("Aucune donnée disponible")

    try:
      df = pd.DataFrame(data)
      df['open_time'] = pd.to_datetime(df['open_time'])

      # Déterminer les couleurs (vert si close > open, rouge sinon)
      colors = ['#00d4aa' if row['close'] >= row['open'] else '#ff4757'
                for _, row in df.iterrows()]

      fig = go.Figure()

      fig.add_trace(go.Bar(
        x=df['open_time'],
        y=df['volume'],
        name='Volume',
        marker_color=colors
      ))

      fig.update_layout(
        template='plotly_dark',
        xaxis_title='Date',
        yaxis_title='Volume',
        hovermode='x unified',
        showlegend=False,
        height=300,
        margin=dict(l=50, r=50, t=30, b=50)
      )

      return fig

    except Exception as e:
      logger.error(f"Erreur lors de la création du graphique de volume: {e}")
      return create_empty_figure("Erreur lors du chargement")

  @app.callback(
    Output('indicators-chart', 'figure'),
    Input('historical-data-store', 'data')
  )
  def update_indicators_chart(data):
    """Met à jour le graphique des indicateurs techniques."""
    if not data:
      return create_empty_figure("Aucune donnée disponible")

    try:
      df = pd.DataFrame(data)
      df['open_time'] = pd.to_datetime(df['open_time'])

      # Calculer RSI
      df['rsi'] = calculate_rsi(df['close'])

      fig = go.Figure()

      # RSI
      fig.add_trace(go.Scatter(
        x=df['open_time'],
        y=df['rsi'],
        mode='lines',
        name='RSI (14)',
        line=dict(color='#ffa502', width=2)
      ))

      # Lignes de référence RSI
      fig.add_hline(y=70, line_dash="dash", line_color="red",
                    annotation_text="Suracheté (70)")
      fig.add_hline(y=30, line_dash="dash", line_color="green",
                    annotation_text="Survendu (30)")

      fig.update_layout(
        template='plotly_dark',
        xaxis_title='Date',
        yaxis_title='RSI',
        hovermode='x unified',
        showlegend=True,
        height=300,
        margin=dict(l=50, r=50, t=30, b=50),
        yaxis=dict(range=[0, 100])
      )

      return fig

    except Exception as e:
      logger.error(f"Erreur lors de la création du graphique d'indicateurs: {e}")
      return create_empty_figure("Erreur lors du chargement")

  @app.callback(
    [Output('streaming-status', 'children'),
     Output('last-trade', 'children'),
     Output('streaming-interval', 'disabled')],
    [Input('streaming-toggle', 'value'),
     Input('streaming-interval', 'n_intervals')],
    [State('symbol-dropdown', 'value')]
  )
  def toggle_streaming(enabled, n_intervals, symbol):
    """Streaming temps réel via API Binance."""
    if not enabled:
      return "⚪ Streaming désactivé", "", True

    if not symbol:
      return "🔴 Streaming actif", "⚠️ Sélectionnez une cryptomonnaie", False

    try:
      # Appel direct à l'API Binance pour le ticker 24h en temps réel
      response = requests.get(
        "https://api.binance.com/api/v3/ticker/24hr",
        params={'symbol': symbol},
        timeout=3,
        proxies={'http': None, 'https': None}  # Bypass proxy si configuré
      )
      response.raise_for_status()
      data = response.json()

      price = float(data['lastPrice'])
      change_pct = float(data['priceChangePercent'])
      high = float(data['highPrice'])
      low = float(data['lowPrice'])
      volume = float(data['quoteVolume'])

      from zoneinfo import ZoneInfo
      now = datetime.now(ZoneInfo('Europe/Paris')).strftime('%H:%M:%S')

      color = "#00d4aa" if change_pct >= 0 else "#ff4757"
      sign = "+" if change_pct >= 0 else ""
      arrow = "▲" if change_pct >= 0 else "▼"

      content = html.Div([
        html.Div([
          html.Strong(f"⚡ {symbol}", className="text-primary"),
          html.Span(f"  •  {now}", className="text-muted ms-2 small"),
        ], className="mb-1"),
        html.Div([
          html.Span(
            f"${price:,.2f}",
            style={"fontSize": "1.8rem", "fontWeight": "bold", "color": color}
          ),
          html.Span(
            f"  {arrow} {sign}{change_pct:.2f}%",
            style={"color": color, "fontSize": "1.1rem", "marginLeft": "12px"}
          ),
        ], className="mb-1"),
        html.Hr(style={"borderColor": "#495057", "margin": "6px 0"}),
        html.Small([
          html.Span("24h  ", className="text-muted"),
          html.Span(f"Haut: ${high:,.2f}  ", className="text-success"),
          html.Span(f"Bas: ${low:,.2f}  ", className="text-danger"),
          html.Span(f"Vol: ${volume:,.0f}", className="text-info"),
        ]),
      ])

      return "🔴 Live Binance", content, False

    except requests.exceptions.RequestException as e:
      logger.error(f"Erreur API Binance: {e}")
      return "🔴 Streaming actif", html.Span(
        "❌ API Binance inaccessible (vérifiez la connexion Internet du container)",
        className="text-danger"
      ), False
    except Exception as e:
      logger.error(f"Erreur streaming: {e}")
      return "🔴 Streaming actif", html.Span(
        f"❌ Erreur: {str(e)[:120]}", className="text-danger"
      ), False


def calculate_rsi(prices, period=14):
  """Calcule le RSI (Relative Strength Index)."""
  delta = prices.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

  rs = gain / loss
  rsi = 100 - (100 / (1 + rs))

  return rsi


def create_empty_figure(message):
  """Crée un graphique vide avec un message."""
  fig = go.Figure()

  fig.add_annotation(
    text=message,
    xref="paper",
    yref="paper",
    x=0.5,
    y=0.5,
    showarrow=False,
    font=dict(size=16, color="gray")
  )

  fig.update_layout(
    template='plotly_dark',
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    height=300
  )

  return fig
