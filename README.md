# TradeQuant

TradeQuant is a modular Python-based trading strategy research and backtesting framework designed for systematic strategy development, walk-forward validation, and risk analysis.

---

## Features

- OHLC-based backtesting engine
- Intra-candle SL/TP execution logic
- R-multiple performance analytics
- Maximum drawdown tracking
- Walk-forward validation
- Portfolio-level strategy evaluation
- Risk simulation & stress testing
- Streamlit dashboard interface
- Data gap detection

---

## Architecture

- data\*.csv – BTCUSDT Historical data
- loader.py – Data ingestion & preprocessing
- strategy.py – Strategy signal logic
- trade.py – Trade lifecycle management
- backtester.py – Core execution engine
- metrics.py – Performance analytics
- walk_forward_runner.py – Walk-forward validation
- portfolio_runner.py – Multi-strategy evaluation
- risk_simulation.py – Risk modeling
- ui/app.py – Streamlit dashboard

---

## Data

This project uses years of historical data across:

- 1-minute timeframe
- 5-minute timeframe
- 15-minute timeframe

Expected MT5 export format:

<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>

---

## Installation

Clone repository:

git clone https://github.com/AbduhHub/tradequant.git
cd tradequant

Create virtual environment:

python -m venv venv
venv\Scripts\activate (Windows)
source venv/bin/activate (Mac/Linux)

Install dependencies:

pip install -r requirements.txt

---

## Running the Engine

CLI execution:

python main.py

Streamlit dashboard:

streamlit run ui/app.py

---

## Performance Metrics

- Win Rate
- Expectancy (R-based)
- Total R
- Maximum Drawdown
- Trade Count

---

## Disclaimer

This project is for research and educational purposes only.
It does not constitute financial advice.
