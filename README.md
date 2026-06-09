<div align="center">

# TradeQuant

### Quantitative Strategy Research Platform

**Backtest · Optimize · Simulate · Validate**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://tradequant.onrender.com)
[![Live Demo](https://img.shields.io/badge/Live_Demo-tradequant.onrender.com-00C7B7?style=flat&logo=render&logoColor=white)](https://tradequant.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

[**Live Demo →**](https://tradequant.onrender.com) &nbsp;|&nbsp; [**Source Code →**](https://github.com/AbduhHub/TradeQuant)

</div>

---

## Overview

TradeQuant is a full-stack quantitative trading research platform built in Python. It backtests rule-based strategies on 7 years of historical data across **3 instruments** (BTCUSD, XAUUSD, EURUSD) and **8 timeframes** (M1 → W1), with realistic per-instrument transaction cost modeling, dynamic position sizing, and a complete analytical suite covering parameter optimization, Monte Carlo risk simulation, and walk-forward validation.

The platform is deployed publicly and includes an interactive 11-tab Streamlit research dashboard backed by a pre-computed results cache covering 126+ strategy combinations.

---

## Live Demo

> **[https://tradequant.onrender.com](https://tradequant.onrender.com)**

No installation required. The dashboard loads pre-computed results instantly — no waiting for backtests to run.

---

## Key Features

| Module                      | What it does                                                                                                                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Vectorized Data Loader**  | Parses MT5 tab-separated CSV for all 8 timeframes including Daily/Weekly (date-only format). Uses `numpy` arrays instead of `iterrows()` — 6× faster on 1.6M-row M1 datasets                     |
| **Gap Detection**           | Vectorized `numpy.diff()` gap detection covering both time gaps and price gaps (>0.5%). Weekend-aware for forex/gold. Forces open trade closure at gap-open price                                |
| **Transaction Cost Model**  | Per-instrument costs in correct price-unit basis: USD/BTC for crypto, USD/oz for gold, USD/EUR-unit for forex. Eliminates the "zero cost" simulation bias                                        |
| **Dynamic Position Sizing** | Risk-based sizing: `size = (capital × risk%) / sl_distance`. Instrument-aware max-lot caps. Supports Fixed %, Kelly Criterion, ATR-based, and Optimal-F                                          |
| **4 Trading Strategies**    | Trend Pullback V3 (ATR stops + momentum confirm), Break Retest (cooldown), Inside Bar (mother bar stops), Liquidity Sweep (swing-structure reversal)                                             |
| **Grid Search Optimizer**   | Exhaustive parameter sweep over configurable grid using `itertools.product`. Ranks results by avg R, total R, or win rate with minimum-trade filter                                              |
| **Monte Carlo Simulator**   | Bootstrap resampling over trade R-multiples. Reports risk of ruin, return percentiles (P5–P95), drawdown exceedance probabilities                                                                |
| **Walk-Forward Tester**     | Rolling window optimization (12mo in-sample / 3mo out-of-sample). Tracks degradation and consistency across all windows                                                                          |
| **Risk Controller**         | 6 independent trading limits: daily loss, weekly loss, max drawdown, consecutive losses, daily trade count, min time between trades                                                              |
| **SQLAlchemy Database**     | ORM-based persistence of backtest configs, individual trades, and metrics. Three-table schema with cascade relationships                                                                         |
| **Streamlit Dashboard**     | 11-tab research interface: Overview, Equity & DD, Trade Ledger, Cost Analysis, Instrument Comparison, Timeframe Comparison, Grid Search, Monte Carlo, Walk-Forward, Risk Controller, All Results |
| **Pre-computed Cache**      | `run_all_tests.py` runs all 126+ combinations overnight and saves to JSON + CSV. Dashboard loads results instantly — no recompute on page load                                                   |

---

## Architecture

```
trading_engine/
│
├── data/                          # MT5-exported CSV files (not tracked in git)
│   ├── BTC_M1.csv / BTCUSD_H1.csv / BTCUSD_Daily.csv ...
│   ├── XAU_M1.csv / XAUUSD_H1.csv ...
│   └── EUR_M1.csv / EURUSD_H1.csv ...
│
├── strategies/
│   ├── trend_pullback_v3_FIXED.py  # ATR-based stops + momentum confirmation
│   ├── break_retest.py             # Breakout + retest with cooldown
│   ├── inside_bar.py               # Mother bar pattern
│   └── liquidity_sweep.py          # Swing-structure reversal
│
├── costs/
│   └── transaction_costs.py        # Per-instrument cost model (spread+slippage+commission)
│
├── risk/
│   ├── position_sizer.py           # Fixed%, Kelly, ATR-based, Optimal-F
│   └── risk_controller.py          # 6-limit trade permission system
│
├── optimization/
│   └── grid_search.py              # Exhaustive parameter sweep
│
├── simulation/
│   └── monte_carlo.py              # Bootstrap resampling simulator
│
├── validation/
│   └── walk_forward.py             # Rolling window optimization + OOS testing
│
├── database/
│   ├── models.py                   # SQLAlchemy ORM (Backtest, Trade, Metrics)
│   ├── repository.py               # CRUD data access layer
│   └── connection.py               # Engine + session management
│
├── ui/
│   └── app.py                      # Streamlit 11-tab dashboard
│
├── loader_enhanced.py              # Vectorized MT5 CSV loader + gap detection
├── backtester.py                   # Core simulation loop + instrument-aware sizing
├── trade.py                        # Trade lifecycle + SL/TP + cost application
├── metrics.py                      # R-based + dollar performance statistics
├── strategy_factory.py             # Strategy registry + instantiation
├── structure.py                    # Swing high/low detection
├── run_all_tests.py                # Supreme test runner (all combinations)
│
├── results_cache.json              # Pre-computed results for dashboard Tab 11
├── results_full.csv                # All backtest results
├── results_grid_search.csv         # Grid search top results
├── results_walk_forward.csv        # Walk-forward per-window results
├── results_monte_carlo.csv         # Monte Carlo statistics
└── results_position_sizing.csv     # Position sizing comparison
```

---

## Results Summary

All results use **$10,000 initial capital**, **1% risk per trade**, **costs enabled**, **full 7-year history (2018–2025)**.

### Top Performing Combinations (Costs ON)

| Symbol | Timeframe | Strategy       | Trades | Avg R  | Net P&L  | Return |
| ------ | --------- | -------------- | ------ | ------ | -------- | ------ |
| EURUSD | H4        | Break Retest   | 512    | +0.247 | +$22,301 | +223%  |
| EURUSD | H1        | Trend Pullback | 897    | +0.100 | +$12,274 | +123%  |
| XAUUSD | H4        | Break Retest   | 504    | +0.172 | +$11,907 | +119%  |
| BTCUSD | H4        | Break Retest   | 563    | +0.122 | +$8,038  | +80%   |
| XAUUSD | H4        | Inside Bar     | 129    | +0.455 | +$7,530  | +75%   |

### Cost Impact (Same strategy, costs ON vs OFF)

| Setup                    | Without Costs | With Costs   | Cost Drag     |
| ------------------------ | ------------- | ------------ | ------------- |
| BTCUSD M1 Trend Pullback | −0.004 avg R  | −2.019 avg R | −2.015R/trade |
| EURUSD H4 Break Retest   | +0.364 avg R  | +0.247 avg R | −0.117R/trade |
| EURUSD H1 Trend Pullback | +0.237 avg R  | +0.100 avg R | −0.137R/trade |

> **Key finding:** The same strategy logic that destroys capital at M1 (−$12,694) produces +$22,301 at H4. Cost impact is timeframe-dependent, not strategy-dependent.

### Walk-Forward Validation (EURUSD H1 Trend Pullback)

| Metric                 | Value                          |
| ---------------------- | ------------------------------ |
| Windows tested         | 75 (12-month in / 3-month out) |
| In-sample avg R        | +0.199                         |
| Out-of-sample avg R    | +0.168                         |
| Degradation            | 15.9%                          |
| Windows profitable OOS | 64%                            |

### Monte Carlo (5,000 simulations — EURUSD H4 Break Retest)

| Metric                 | Value             |
| ---------------------- | ----------------- |
| Risk of ruin           | 0.0%              |
| Probability profitable | 99.8%             |
| Median return          | +220.3%           |
| P5 / P95 final equity  | $8,241 / $132,057 |

---

## Installation

```bash
# Clone
git clone https://github.com/AbduhHub/TradeQuant.git
cd TradeQuant

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate      # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Requirements

```
streamlit
pandas
numpy
plotly
sqlalchemy
```

---

## Usage

### Run the Dashboard

```bash
streamlit run ui/app.py
```

Opens at `http://localhost:8501`. Select instrument, timeframe, strategy, and capital from the sidebar — click **Run Backtest**.

### Run All Tests (Pre-compute Everything)

```bash
python run_all_tests.py
```

Runs all 126+ backtest combinations + grid search + walk-forward + Monte Carlo overnight. Saves results to `results_cache.json` and CSV files. Dashboard Tab 11 then loads all results instantly.

### Data Format

Place MT5-exported CSV files in the `data/` folder. Expected naming convention and format:

| Timeframe      | Filename                                 | Format                         |
| -------------- | ---------------------------------------- | ------------------------------ |
| M1, M5, M15    | `BTC_M1.csv`, `XAU_M1.csv`, `EUR_M1.csv` | `<DATE>\t<TIME>\t<OPEN>...`    |
| H1, H4, D1, W1 | `BTCUSD_H1.csv`, `XAUUSD_Daily.csv`      | Same MT5 tab-separated         |
| Daily / Weekly | `BTCUSD_Daily.csv`                       | `<DATE>` only (no TIME column) |

---

## Tech Stack

| Technology          | Role                                                 |
| ------------------- | ---------------------------------------------------- |
| Python 3.12         | Core language                                        |
| Pandas + NumPy      | Data processing (vectorized, no iterrows)            |
| Plotly              | Interactive charts (candlestick, equity, histograms) |
| Streamlit           | Web dashboard                                        |
| SQLAlchemy + SQLite | ORM database layer                                   |
| itertools           | Grid search parameter combinations                   |

---

## Engineering Highlights

- **Vectorized pipeline** — `numpy.diff()` gap detection processes 1.6M candles in 0.17s vs ~40s with Python loops
- **Instrument-aware position sizing** — unified `size = risk / sl_distance` formula works correctly across crypto, gold, and forex without per-instrument case logic
- **Per-instrument cost basis** — costs expressed in USD per base unit (USD/BTC, USD/oz, USD/EUR-unit) so `gross_pnl = price_diff × size` is always in the same unit as costs
- **Cache-backed dashboard** — `@st.cache_data` on data loading + gap detection; pre-computed JSON cache for results — repeat runs return in <0.1s
- **Modular strategy interface** — adding a new strategy requires one file implementing `on_candle(index) → Trade | None`; zero changes to backtester, cost model, or UI

---

## Academic Context

This project was developed as a final year B.Tech Computer Science Engineering capstone project at Sharnbasva University, Kalaburagi. The 7th semester phase built the core engine; the 8th semester phase added all advanced modules documented in this repository.

---

## Disclaimer

This project is for research and educational purposes only. It does not constitute financial advice. Past backtest performance does not guarantee future results.

---

<div align="center">

Built by [Abdullah](https://github.com/AbduhHub) &nbsp;·&nbsp; [Live Demo](https://tradequant.onrender.com) &nbsp;·&nbsp; [Report Issues](https://github.com/AbduhHub/TradeQuant/issues)

</div>
