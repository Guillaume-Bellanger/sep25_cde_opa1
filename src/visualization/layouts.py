"""
Layouts pour le dashboard Dash
"""
import dash_bootstrap_components as dbc
from dash import html, dcc


def create_layout():
  """Crée le layout principal du dashboard."""

  return dbc.Container([
    # Header
    dbc.Row([
      dbc.Col([
        html.H1("🚀 Crypto Dashboard", className="text-center text-primary mb-3"),
        html.H5("Analyse en temps réel des cryptomonnaies",
                className="text-center text-muted mb-4")
      ])
    ]),

    # Controls
    dbc.Row([
      dbc.Col([
        dbc.Card([
          dbc.CardBody([
            html.Label("Cryptomonnaie", className="fw-bold"),
            dbc.Select(
              id='symbol-dropdown',
              options=[
                {'label': 'BTCUSDT ⭐', 'value': 'BTCUSDT'},
                {'label': 'ETHUSDT', 'value': 'ETHUSDT'},
                {'label': 'SOLUSDT', 'value': 'SOLUSDT'},
              ],
              value='BTCUSDT',
              className="mb-3"
            ),

            html.Label("Période", className="fw-bold"),
            dbc.Select(
              id='period-dropdown',
              options=[
                {'label': '24 heures', 'value': '1'},
                {'label': '7 jours', 'value': '7'},
                {'label': '30 jours', 'value': '30'},
                {'label': '90 jours', 'value': '90'},
                {'label': '1 an', 'value': '365'}
              ],
              value='7',
              className="mb-3"
            ),

            html.Label("Intervalle", className="fw-bold"),
            dbc.Select(
              id='interval-dropdown',
              options=[
                {'label': '1d', 'value': '1d'},
              ],
              value='1d',
              className="mb-3"
            ),

            dbc.Button(
              "🔄 Actualiser",
              id="refresh-button",
              color="primary",
              className="w-100",
              n_clicks=0
            )
          ])
        ], className="shadow-sm")
      ], md=3),

      # Main content
      dbc.Col([
        # Stats cards
        dbc.Row([
          dbc.Col([
            create_stat_card("current-price", "Prix actuel", "💰", "primary")
          ], md=3),
          dbc.Col([
            create_stat_card("price-change", "Variation 24h", "📈", "success")
          ], md=3),
          dbc.Col([
            create_stat_card("volume-24h", "Volume 24h", "📊", "info")
          ], md=3),
          dbc.Col([
            create_stat_card("high-low", "Max / Min", "🎯", "warning")
          ], md=3),
        ], className="mb-4"),

        # Price chart
        dbc.Card([
          dbc.CardHeader([
            html.H5("📈 Graphique des prix", className="mb-0")
          ]),
          dbc.CardBody([
            dcc.Loading(
              dcc.Graph(id='price-chart', config={'displayModeBar': False}),
              type="default"
            )
          ])
        ], className="shadow-sm mb-4"),

        # Volume chart
        dbc.Card([
          dbc.CardHeader([
            html.H5("📊 Volume de trading", className="mb-0")
          ]),
          dbc.CardBody([
            dcc.Loading(
              dcc.Graph(id='volume-chart', config={'displayModeBar': False}),
              type="default"
            )
          ])
        ], className="shadow-sm mb-4"),

        # Technical indicators
        dbc.Card([
          dbc.CardHeader([
            html.H5("📉 Indicateurs techniques", className="mb-0")
          ]),
          dbc.CardBody([
            dcc.Loading(
              dcc.Graph(id='indicators-chart', config={'displayModeBar': False}),
              type="default"
            )
          ])
        ], className="shadow-sm"),

      ], md=9)
    ]),

    # Streaming section (optionnel)
    dbc.Row([
      dbc.Col([
        dbc.Card([
          dbc.CardHeader([
            html.H5("🔴 Données en temps réel", className="mb-0 d-inline"),
            dbc.Switch(
              id="streaming-toggle",
              label="Activer le streaming",
              value=False,
              className="float-end"
            )
          ]),
          dbc.CardBody([
            html.Div(id="streaming-status", className="text-muted mb-2"),
            html.Div(id="last-trade", className="fs-5")
          ])
        ], className="shadow-sm mt-4")
      ])
    ]),

    # Auto-refresh interval
    dcc.Interval(
      id='auto-refresh-interval',
      interval=60 * 1000,  # 60 secondes
      n_intervals=0,
      disabled=True
    ),

    # Streaming interval (pour le streaming temps réel)
    dcc.Interval(
      id='streaming-interval',
      interval=3 * 1000,  # 3 secondes
      n_intervals=0,
      disabled=True
    ),

    # Store for data
    dcc.Store(id='historical-data-store'),

  ], fluid=True, className="py-4")


def create_stat_card(card_id, title, icon, color):
  """Crée une carte de statistique."""
  return dbc.Card([
    dbc.CardBody([
      html.Div([
        html.Span(icon, className="fs-3 me-2"),
        html.Span(title, className="text-muted")
      ], className="d-flex align-items-center mb-2"),
      html.H4(id=card_id, className=f"text-{color} mb-0", children="--")
    ])
  ], className=f"shadow-sm border-{color} border-start border-4")
