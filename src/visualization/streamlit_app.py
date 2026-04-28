"""
CryptoBot ML — Streamlit dashboard.

All data is fetched from the FastAPI backend (no direct DB access).
Set API_BASE_URL env var to point at the API (default: http://localhost:8001).
"""
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
SIGNAL_COLOR: Dict[str, str] = {
    "BUY":  "#00C853",
    "SELL": "#D50000",
    "HOLD": "#FF8F00",
}

st.set_page_config(
    page_title="CryptoBot ML",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def api_get(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Cached GET (TTL 60 s) — use for read-only endpoints."""
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.warning(f"API `{endpoint}` → HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"API inaccessible ({API_BASE_URL}) : {e}")
        return None


def api_get_live(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Non-cached GET — for /predict and real-time status calls."""
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.warning(f"API `{endpoint}` → HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"API inaccessible ({API_BASE_URL}) : {e}")
        return None

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("📊 CryptoBot ML")
st.sidebar.caption(f"API : `{API_BASE_URL}`")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📈 Marché", "🤖 Signaux ML", "📊 Indicateurs", "⚙️ Modèle", "🔍 Monitoring"],
)

# ---------------------------------------------------------------------------
# Page : Marché
# ---------------------------------------------------------------------------
if page == "📈 Marché":
    st.title("📈 Marché")

    c1, c2, c3 = st.columns(3)
    symbol   = c1.selectbox("Symbole",    SYMBOLS,            key="mkt_sym")
    interval = c2.selectbox("Intervalle", ["1h", "4h", "1d"], key="mkt_int")
    limit    = c3.slider("Bougies",       50, 500, 200,        key="mkt_lim")

    raw = api_get(f"/api/historical/{symbol}", {"interval": interval, "limit": limit})

    if raw:
        df = pd.DataFrame(raw)
        df["open_time"] = pd.to_datetime(df["open_time"])

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.75, 0.25], vertical_spacing=0.02,
        )
        fig.add_trace(go.Candlestick(
            x=df["open_time"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"], name="OHLC",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=df["open_time"], y=df["volume"], name="Volume",
            marker_color="rgba(100,149,237,0.5)",
        ), row=2, col=1)
        fig.update_layout(
            title=f"{symbol} — {interval}",
            xaxis_rangeslider_visible=False,
            height=540, template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        last, prev = df.iloc[-1], df.iloc[-2]
        pct = (last["close"] - prev["close"]) / prev["close"] * 100
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Prix",   f"${last['close']:,.2f}", f"{pct:+.2f}%")
        m2.metric("Haut",   f"${last['high']:,.2f}")
        m3.metric("Bas",    f"${last['low']:,.2f}")
        m4.metric("Volume", f"{last['volume']:,.0f}")
    else:
        st.info("Données indisponibles — vérifiez que l'API et MongoDB sont démarrés.")

# ---------------------------------------------------------------------------
# Page : Signaux ML
# ---------------------------------------------------------------------------
elif page == "🤖 Signaux ML":
    st.title("🤖 Signaux ML")

    c1, c2 = st.columns([3, 1])
    symbol = c1.selectbox("Symbole", SYMBOLS, key="sig_sym")

    if "predictions" not in st.session_state:
        st.session_state.predictions = {}

    c2.write("")
    c2.write("")
    if c2.button("🔄 Générer signal"):
        with st.spinner("Prédiction en cours…"):
            pred = api_get_live("/predict", {"symbol": symbol})
            if pred:
                st.session_state.predictions[symbol] = pred

    pred = st.session_state.predictions.get(symbol)
    if pred:
        label = pred["signal_label"]
        color = SIGNAL_COLOR.get(label, "#888888")
        st.markdown(
            f'<div style="background:{color};padding:20px 24px;border-radius:12px;'
            f'text-align:center;margin-bottom:12px;">'
            f'<h1 style="color:white;margin:0;font-size:2.8rem;">{label}</h1>'
            f'<p style="color:white;margin:6px 0 0;font-size:1.1rem;">'
            f'Confiance : <strong>{pred["confidence"]:.1%}</strong></p></div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        a, b, c = st.columns(3)
        a.metric("Prix",      f"${pred['price']:,.2f}")
        b.metric("Timestamp", str(pred["timestamp"])[:19])
        c.metric("Modèle",    pred["model_version"].split("_")[1])
    else:
        st.info("Cliquez sur **Générer signal** pour lancer une prédiction.")

    st.markdown("---")
    st.subheader("Historique des signaux")

    hist = api_get("/signal/history", {"symbol": symbol, "limit": 50})
    if hist:
        df_h = pd.DataFrame(hist)
        df_h["timestamp"] = pd.to_datetime(df_h["timestamp"])

        fig = go.Figure(go.Bar(
            x=df_h["timestamp"],
            y=df_h["confidence"],
            marker_color=[SIGNAL_COLOR.get(l, "#888") for l in df_h["signal_label"]],
            text=df_h["signal_label"],
            textposition="outside",
        ))
        fig.update_layout(
            title=f"Historique des signaux — {symbol}",
            yaxis_title="Confidence", yaxis_range=[0, 1.15],
            height=320, template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_h[["timestamp", "signal_label", "confidence", "model_version"]]
            .sort_values("timestamp", ascending=False)
            .reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("Aucun historique — lancez au moins une prédiction via le bouton ci-dessus.")

# ---------------------------------------------------------------------------
# Page : Indicateurs
# ---------------------------------------------------------------------------
elif page == "📊 Indicateurs":
    st.title("📊 Indicateurs techniques")

    c1, c2 = st.columns(2)
    symbol = c1.selectbox("Symbole", SYMBOLS,      key="ind_sym")
    limit  = c2.slider("Bougies",    50, 300, 120, key="ind_lim")

    raw = api_get("/features", {"symbol": symbol, "limit": limit})

    if raw:
        df = pd.DataFrame(raw)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Bollinger Bands + prix
        st.subheader("Prix & Bandes de Bollinger")
        fig_bb = go.Figure()
        fig_bb.add_trace(go.Scatter(
            x=df["timestamp"], y=df["bb_upper"], name="BB Upper",
            line=dict(color="rgba(100,200,255,0.5)", dash="dot"),
        ))
        fig_bb.add_trace(go.Scatter(
            x=df["timestamp"], y=df["bb_lower"], name="BB Lower",
            line=dict(color="rgba(100,200,255,0.5)", dash="dot"),
            fill="tonexty", fillcolor="rgba(100,200,255,0.06)",
        ))
        fig_bb.add_trace(go.Scatter(
            x=df["timestamp"], y=df["bb_mid"], name="BB Mid",
            line=dict(color="rgba(100,200,255,0.35)", dash="dash"),
        ))
        fig_bb.add_trace(go.Scatter(
            x=df["timestamp"], y=df["close"], name="Close",
            line=dict(color="white", width=1.5),
        ))
        fig_bb.update_layout(
            height=350, template="plotly_dark",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_bb, use_container_width=True)

        # RSI
        st.subheader("RSI (14)")
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df["timestamp"], y=df["rsi_14"], name="RSI 14",
            line=dict(color="#FFD700"),
        ))
        fig_rsi.add_hline(y=70, line_dash="dot", line_color="red",
                           annotation_text="Surachat 70")
        fig_rsi.add_hline(y=30, line_dash="dot", line_color="green",
                           annotation_text="Survente 30")
        fig_rsi.update_layout(
            height=230, yaxis_range=[0, 100], template="plotly_dark",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

        # MACD
        st.subheader("MACD")
        fig_macd = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.45], vertical_spacing=0.04,
        )
        fig_macd.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd"], name="MACD",
            line=dict(color="#00BFFF"),
        ), row=1, col=1)
        fig_macd.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd_signal"], name="Signal",
            line=dict(color="#FF6347"),
        ), row=1, col=1)
        hist_colors = [
            "#00C853" if v >= 0 else "#D50000"
            for v in df["macd_hist"].fillna(0)
        ]
        fig_macd.add_trace(go.Bar(
            x=df["timestamp"], y=df["macd_hist"],
            name="Histogramme", marker_color=hist_colors,
        ), row=2, col=1)
        fig_macd.update_layout(
            height=350, template="plotly_dark",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_macd, use_container_width=True)

    else:
        st.info("Données de features indisponibles — vérifiez que l'API et PostgreSQL sont démarrés.")

# ---------------------------------------------------------------------------
# Page : Modèle
# ---------------------------------------------------------------------------
elif page == "⚙️ Modèle":
    st.title("⚙️ Métriques du modèle")

    metrics = api_get("/model/metrics")
    if metrics:
        for m in metrics:
            with st.expander(
                f"**{m['symbol']}** — {m['model_name'].upper()}",
                expanded=True,
            ):
                a, b, c = st.columns(3)
                a.metric("Accuracy",     f"{m['accuracy']:.1%}")
                b.metric("F1 macro",     f"{m['f1_macro']:.3f}")
                c.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.3f}")

                d, e, f_ = st.columns(3)
                d.metric("Train", f"{m['n_train']} lignes")
                e.metric("Val",   f"{m['n_val']} lignes")
                f_.metric("Test", f"{m['n_test']} lignes")

                st.caption(
                    f"Version : `{m['model_version']}` · "
                    f"Entraîné le {m['date_train'][:10]}"
                )
    else:
        st.info("Métriques indisponibles — vérifiez que l'API est démarrée.")

# ---------------------------------------------------------------------------
# Page : Monitoring
# ---------------------------------------------------------------------------
elif page == "🔍 Monitoring":
    st.title("🔍 Monitoring")

    c_left, c_right = st.columns(2)

    with c_left:
        st.subheader("Statut des services")

        health = api_get_live("/health")
        if health:
            ok = health.get("status") == "healthy"
            ml = health.get("model_loaded", False)
            st.markdown(f"{'🟢' if ok else '🔴'} **API FastAPI** : `{health.get('status', '?')}`")
            st.markdown(f"{'🟢' if ml else '🔴'} **Modèle ML chargé** : `{ml}`")
        else:
            st.markdown("🔴 **API FastAPI** : inaccessible")

        st.markdown("")
        streams = api_get_live("/api/stream/active")
        if streams:
            active = streams.get("active_streams", [])
            st.markdown(
                f"{'🟢' if active else '⚪'} **WebSocket streams actifs** : {len(active)}"
            )
            for s in active:
                st.markdown(f"  - `{s['symbol']}` — {s['connected_clients']} client(s)")

    with c_right:
        st.subheader("Liens & interfaces")
        st.markdown("""
| Service | URL |
|---|---|
| API Swagger | http://localhost:8001/docs |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Airflow | http://localhost:8080 |
| PgAdmin | http://localhost:5436 |
        """)

    st.markdown("---")
    st.subheader("Symboles disponibles en base")
    sym_data = api_get("/api/symbols")
    if sym_data:
        syms = sym_data.get("symbols", [])
        st.write(", ".join(syms) if syms else "Aucun symbole trouvé.")
    else:
        st.info("MongoDB indisponible.")
