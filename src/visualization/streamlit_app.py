"""
CryptoBot ML — Streamlit dashboard.

All data is fetched from the FastAPI backend (no direct DB access).
Set API_BASE_URL env var to point at the API (default: http://localhost:8001).
"""
import os
import time
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
# Sidebar — redirect handler (must run before any widget with key="nav")
# ---------------------------------------------------------------------------
if "goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("goto")

st.sidebar.title("📊 CryptoBot ML")
st.sidebar.caption(f"API : `{API_BASE_URL}`")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🎯 Démo", "🔴 Live", "📈 Marché", "🤖 Signaux ML", "📊 Indicateurs", "⚙️ Modèle", "🔍 Monitoring"],
    key="nav",
)

# ---------------------------------------------------------------------------
# Page : Démo
# ---------------------------------------------------------------------------
if page == "🎯 Démo":
    st.title("🎯 Démo — CryptoBot ML")
    st.caption("Vue d'ensemble pour la soutenance — tous les services en un clin d'œil.")

    # ── 1. Accès rapide ──────────────────────────────────────────────────────
    st.markdown("### Accès rapide")
    btn1, btn2, btn3, btn4 = st.columns(4)
    btn1.link_button("🌊 Airflow",     "http://localhost:8080",      use_container_width=True)
    btn2.link_button("📊 Grafana",     "http://localhost:3000",      use_container_width=True)
    btn3.link_button("📖 Swagger API", "http://localhost:8001/docs", use_container_width=True)
    btn4.link_button("🔬 Prometheus",  "http://localhost:9090",      use_container_width=True)

    st.markdown("---")

    # ── 2. Signaux ML BTC / ETH / SOL ────────────────────────────────────────
    hd, refresh_btn = st.columns([5, 1])
    hd.markdown("### Signaux ML actuels — BTC · ETH · SOL")
    with refresh_btn:
        st.write("")
        if st.button("🔄", help="Actualiser les signaux", key="demo_refresh"):
            st.rerun()

    col_btc, col_eth, col_sol = st.columns(3)

    def _signal_card(col, sym: str) -> None:
        with col:
            pred = api_get_live("/predict", {"symbol": sym})
            if pred:
                label  = pred.get("signal_label", "–")
                conf   = pred.get("confidence", 0.0)
                price  = pred.get("price", 0.0)
                color  = SIGNAL_COLOR.get(label, "#444")
                model  = pred.get("model_version", "")
                # algo tag: xgboost → XGB, lightgbm → LGB
                algo   = "XGB" if "xgboost" in model else ("LGB" if "lgb" in model else "ML")
                st.markdown(
                    f'<div style="background:{color};border-radius:12px;padding:20px 16px;'
                    f'text-align:center;margin-bottom:4px;">'
                    f'<div style="color:rgba(255,255,255,0.75);font-size:0.8rem;'
                    f'font-weight:700;letter-spacing:1px;">{sym}</div>'
                    f'<div style="color:white;font-size:2.4rem;font-weight:800;'
                    f'line-height:1.1;margin:6px 0 4px;">{label}</div>'
                    f'<div style="color:white;font-size:1rem;">'
                    f'<strong>{conf:.1%}</strong> confiance</div>'
                    f'<div style="color:rgba(255,255,255,0.8);font-size:0.9rem;'
                    f'margin-top:6px;">${price:,.2f}</div>'
                    f'<div style="color:rgba(255,255,255,0.55);font-size:0.72rem;'
                    f'margin-top:4px;">{algo}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#2a2a2a;border:1px solid #444;border-radius:12px;'
                    f'padding:20px 16px;text-align:center;">'
                    f'<div style="color:#888;font-size:0.8rem;font-weight:700;">{sym}</div>'
                    f'<div style="color:#555;font-size:2rem;margin:8px 0;">–</div>'
                    f'<div style="color:#666;font-size:0.8rem;">indisponible</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    for col, sym in [(col_btc, "BTCUSDT"), (col_eth, "ETHUSDT"), (col_sol, "SOLUSDT")]:
        _signal_card(col, sym)

    st.markdown("---")

    # ── 3. Métriques clés des modèles ────────────────────────────────────────
    st.markdown("### Métriques des modèles")
    metrics = api_get("/model/metrics")
    if metrics:
        m_cols = st.columns(len(metrics))
        for col, m in zip(m_cols, metrics):
            with col:
                st.markdown(
                    f'<div style="background:#1e1e2e;border:1px solid #333;border-radius:10px;'
                    f'padding:14px 16px;text-align:center;">'
                    f'<div style="color:#aaa;font-size:0.78rem;font-weight:700;letter-spacing:1px;">'
                    f'{m["symbol"]}</div>'
                    f'<div style="color:white;font-size:0.8rem;margin:4px 0 10px;">'
                    f'{m["model_name"].upper()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                ma, mb, mc = st.columns(3)
                ma.metric("Sharpe", f"{m['sharpe_ratio']:.2f}")
                mb.metric("F1",     f"{m['f1_macro']:.3f}")
                mc.metric("Acc.",   f"{m['accuracy']:.1%}")
                st.caption(f"Entraîné le {m['date_train'][:10]}")
    else:
        st.info("Métriques indisponibles — vérifiez que l'API est démarrée.")

    st.markdown("---")

    # ── 4. Raccourci vers la page Live ───────────────────────────────────────
    st.markdown("### Démo temps réel")
    live_col, info_col = st.columns([1, 2])
    with live_col:
        if st.button(
            "🔴 Ouvrir la page Live",
            use_container_width=True,
            type="primary",
            key="demo_go_live",
        ):
            st.session_state["goto"] = "🔴 Live"
            st.rerun()
    with info_col:
        st.info(
            "Flux WebSocket Binance **1 minute** — signal BUY/SELL/HOLD en continu, "
            "confiance, prix live et **score de précision** en direct."
        )

# ---------------------------------------------------------------------------
# Page : Live
# ---------------------------------------------------------------------------
elif page == "🔴 Live":
    st.title("🔴 Live — Prédictions temps réel (1m)")

    col_sym, col_ctrl, col_refresh = st.columns([2, 1, 1])
    symbol = col_sym.selectbox("Symbole", SYMBOLS, key="live_sym")

    # Fetch current status
    status = api_get_live("/live/status", {"symbol": symbol}) or {}
    running = status.get("running", False)

    with col_ctrl:
        st.write("")
        if not running:
            if st.button("▶ Démarrer", key="live_start"):
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/live/start",
                        params={"symbol": symbol},
                        timeout=30,
                    )
                    r.raise_for_status()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur démarrage : {e}")
        else:
            if st.button("⏹ Arrêter", key="live_stop"):
                try:
                    requests.post(
                        f"{API_BASE_URL}/live/stop",
                        params={"symbol": symbol},
                        timeout=10,
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur arrêt : {e}")

    with col_refresh:
        st.write("")
        auto_refresh = st.toggle("Auto-refresh 5s", value=True, key="live_auto")

    st.markdown("---")

    if not running:
        st.info(
            "Le prédicteur live n'est pas démarré. "
            "Cliquez **▶ Démarrer** pour lancer le flux WebSocket Binance 1m."
        )
    else:
        live_price = status.get("live_price", 0.0)
        live_time  = status.get("live_time", "")
        sig        = status.get("signal") or {}
        score_str  = status.get("score_str", "0/0")
        score_pct  = status.get("score_pct")
        total      = status.get("total_predictions", 0)

        # ── Top KPIs ──────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Prix live", f"${live_price:,.2f}" if live_price else "–")
        k2.metric("Timestamp", live_time[11:19] if live_time else "–")
        k3.metric("Score", score_str,
                  delta=f"{score_pct}%" if score_pct is not None else None)
        k4.metric("Prédictions évaluées", str(total))

        # ── Signal courant ────────────────────────────────────────────────
        st.markdown("### Signal actuel")
        if sig:
            label      = sig.get("signal_label", "–")
            confidence = sig.get("confidence", 0.0)
            sig_price  = sig.get("price", 0.0)
            sig_time   = str(sig.get("timestamp", ""))[:19]
            color      = SIGNAL_COLOR.get(label, "#555555")

            st.markdown(
                f'<div style="background:{color};padding:18px 24px;border-radius:12px;'
                f'text-align:center;margin-bottom:12px;">'
                f'<h1 style="color:white;margin:0;font-size:2.6rem;">{label}</h1>'
                f'<p style="color:white;margin:6px 0 0;font-size:1.1rem;">'
                f'Confiance : <strong>{confidence:.1%}</strong> &nbsp;|&nbsp; '
                f'Prix : <strong>${sig_price:,.2f}</strong> &nbsp;|&nbsp; '
                f'à <strong>{sig_time[11:] if sig_time else "–"}</strong></p></div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "En attente du premier signal (la première bougie de 1m doit se fermer…)"
            )

        # ── Historique des prédictions ────────────────────────────────────
        st.markdown("### Historique (10 dernières prédictions)")
        history = status.get("history", [])
        if history:
            rows = []
            for h in reversed(history):
                evaluated = h.get("evaluated", False)
                correct   = h.get("correct")
                ret_pct   = h.get("actual_ret_pct")
                rows.append({
                    "Heure":       str(h.get("timestamp", ""))[:19],
                    "Signal":      h.get("signal_label", ""),
                    "Conf.":       f"{h.get('confidence', 0):.1%}",
                    "Prix":        f"${h.get('price', 0):,.2f}",
                    "Évalué":      "✓" if evaluated else "…",
                    "Correct":     ("✅" if correct else "❌") if evaluated else "–",
                    "Δ prix (%)":  f"{ret_pct:+.3f}" if ret_pct is not None else "–",
                })
            df_hist = pd.DataFrame(rows)

            # Colour-code the Signal column via a bar-chart axis trick
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

            # Mini bar chart: confidence by prediction
            fig_hist = go.Figure(go.Bar(
                x=list(range(len(history))),
                y=[h.get("confidence", 0) for h in history],
                marker_color=[SIGNAL_COLOR.get(h.get("signal_label", ""), "#888") for h in history],
                text=[h.get("signal_label", "") for h in history],
                textposition="outside",
            ))
            fig_hist.update_layout(
                title="Confiance des dernières prédictions",
                yaxis_range=[0, 1.2], yaxis_title="Confidence",
                height=240, template="plotly_dark",
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("En attente des premières prédictions…")

    # ── Auto-refresh ──────────────────────────────────────────────────────
    if running and auto_refresh:
        time.sleep(5)
        st.rerun()

# ---------------------------------------------------------------------------
# Page : Marché
# ---------------------------------------------------------------------------
elif page == "📈 Marché":
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
