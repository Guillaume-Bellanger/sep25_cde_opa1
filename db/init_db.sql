-- ============================================================
-- CryptoBot ML — PostgreSQL schema
-- Executed automatically by Docker on first container start.
-- Run manually: psql -U <user> -d <db> -f db/init_db.sql
-- ============================================================

-- ------------------------------------------------------------
-- Table: features
-- One row per (symbol, timestamp) candle with all computed features.
-- Column names are normalised from pandas-ta output (no dots).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS features (
    id              BIGSERIAL        PRIMARY KEY,
    timestamp       TIMESTAMPTZ      NOT NULL,
    symbol          VARCHAR(20)      NOT NULL,

    -- OHLCV
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION,
    volume          DOUBLE PRECISION,

    -- Technical indicators
    rsi_14          DOUBLE PRECISION,
    macd            DOUBLE PRECISION,
    macd_hist       DOUBLE PRECISION,
    macd_signal     DOUBLE PRECISION,
    bb_lower        DOUBLE PRECISION,
    bb_mid          DOUBLE PRECISION,
    bb_upper        DOUBLE PRECISION,
    bb_bandwidth    DOUBLE PRECISION,
    bb_percent      DOUBLE PRECISION,
    ema_9           DOUBLE PRECISION,
    ema_21          DOUBLE PRECISION,
    ema_55          DOUBLE PRECISION,
    sma_20          DOUBLE PRECISION,
    sma_50          DOUBLE PRECISION,
    sma_200         DOUBLE PRECISION,
    atr_14          DOUBLE PRECISION,

    -- Temporal features
    hour            SMALLINT,
    day_of_week     SMALLINT,
    hour_sin        DOUBLE PRECISION,
    hour_cos        DOUBLE PRECISION,
    dow_sin         DOUBLE PRECISION,
    dow_cos         DOUBLE PRECISION,

    -- Lag returns  (pct_change over 1, 4, 24 periods on 1h data)
    return_1h       DOUBLE PRECISION,
    return_4h       DOUBLE PRECISION,
    return_24h      DOUBLE PRECISION,

    CONSTRAINT features_symbol_timestamp_uq UNIQUE (symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS features_symbol_ts_idx
    ON features (symbol, timestamp DESC);

-- ------------------------------------------------------------
-- Table: predictions
-- One row per signal emitted by the model.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id              BIGSERIAL        PRIMARY KEY,
    timestamp       TIMESTAMPTZ      NOT NULL,
    symbol          VARCHAR(20)      NOT NULL,
    signal          SMALLINT         NOT NULL,   -- 1=BUY  0=HOLD  -1=SELL
    signal_label    VARCHAR(10)      NOT NULL,   -- 'BUY' | 'HOLD' | 'SELL'
    confidence      DOUBLE PRECISION,
    model_version   VARCHAR(50),
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS predictions_symbol_ts_idx
    ON predictions (symbol, timestamp DESC);

-- ------------------------------------------------------------
-- Table: model_metrics
-- One row per training run, per symbol.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_metrics (
    id              BIGSERIAL        PRIMARY KEY,
    date_train      TIMESTAMPTZ      NOT NULL,
    symbol          VARCHAR(20)      NOT NULL,
    accuracy        DOUBLE PRECISION,
    f1_macro        DOUBLE PRECISION,
    sharpe_ratio    DOUBLE PRECISION,
    model_version   VARCHAR(50)      NOT NULL,
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);
