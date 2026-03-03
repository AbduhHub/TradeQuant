# PATH SETUP
import os, sys, time
from datetime import date, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# IMPORTS
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from loader import detect_gaps
from backtester import Backtester
from strategy_factory import StrategyFactory
from metrics import calculate_metrics

# PAGE CONFIG
st.set_page_config(layout="wide")
st.title("Quant Strategy Research Dashboard")

# CONSTANTS
TF_MAP = {
    "M1": ("BTC_M1.csv", 1),
    "M5": ("BTC_M5.csv", 5),
    "M15": ("BTC_M15.csv", 15),
}

DATA_DIR = os.path.join(ROOT, "data")
MIN_DATE = date(2019, 1, 1)
MAX_DATE = date(2025, 12, 30)
MAX_CHART_CANDLES = 10_000


# DATA LOADER

@st.cache_data(show_spinner=False)
def load_price_data(tf):
    file, _ = TF_MAP[tf]
    df = pd.read_csv(os.path.join(DATA_DIR, file), sep="\t")
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["datetime"] = pd.to_datetime(
        df["date"] + " " + df["time"],
        format="%Y.%m.%d %H:%M:%S"
    )
    return df.sort_values("datetime").reset_index(drop=True)


# SIDEBAR

with st.sidebar:
    st.header("Backtest Settings")

    strategy_key = st.selectbox("Strategy", list(StrategyFactory.STRATEGIES.keys()))
    timeframe = st.selectbox("Timeframe", TF_MAP.keys())

    risk_per_trade = st.selectbox(
        "Risk per Trade",
        [0.0025, 0.005, 0.01],
        format_func=lambda x: f"{x*100:.2f}%"
    )

    st.subheader("Date Range")
    range_mode = st.selectbox(
        "Range Mode",
        ["Full History", "Last 6 Months", "Last 12 Months", "Year", "Custom"]
    )

    start_date = end_date = year = None
    if range_mode == "Year":
        year = st.selectbox("Select Year", list(range(2019, 2026))[::-1])
    elif range_mode == "Custom":
        start_date = st.date_input("Start Date", MIN_DATE, min_value=MIN_DATE, max_value=MAX_DATE)
        end_date = st.date_input("End Date", MAX_DATE, min_value=MIN_DATE, max_value=MAX_DATE)

    chart_candles = st.slider(
        "Visible candles (default view)",
        100, MAX_CHART_CANDLES, 600, 100
    )

    run_bt = st.button("Run Research")
    runtime_placeholder = st.empty()


# LOAD DATA

df_all = load_price_data(timeframe)
df = df_all.copy()
latest = df["datetime"].max().date()

if range_mode == "Last 6 Months":
    df = df[df["datetime"].dt.date >= latest - timedelta(days=180)]
elif range_mode == "Last 12 Months":
    df = df[df["datetime"].dt.date >= latest - timedelta(days=365)]
elif range_mode == "Year":
    df = df[df["datetime"].dt.year == year]
elif range_mode == "Custom":
    df = df[(df["datetime"].dt.date >= start_date) & (df["datetime"].dt.date <= end_date)]

df = df.reset_index(drop=True)
range_start, range_end = df["datetime"].min(), df["datetime"].max()


# TABS

tabs = st.tabs([
    "📊 Overview & Price",
    "📉 Equity & Drawdown",
    "📋 Trade Ledger",
    "🔀 Strategy Comparison",
    "⏱ Timeframe Comparison"
])


# BACKTEST

trades, candles, runtime = [], [], None

if run_bt and not df.empty:
    with st.spinner("Running backtest…"):
        t0 = time.perf_counter()

        candles = [{
            "time": r["datetime"],
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        } for _, r in df.iterrows()]

        _, tf_minutes = TF_MAP[timeframe]
        gaps = detect_gaps(candles, tf_minutes)

        context = {"gaps": gaps}
        if strategy_key == "liquidity_sweep":
            from structure import detect_swings_rolling
            sh, sl = [], []
            for i in range(len(candles)):
                h, l = detect_swings_rolling(candles, gaps, i, lookback=200)
                if h: sh.append(h)
                if l: sl.append(l)
            context.update({"swing_highs": sh, "swing_lows": sl})

        strategy = StrategyFactory.create(strategy_key, candles, context)
        trades = Backtester(candles, gaps, strategy).run()
        runtime = time.perf_counter() - t0

    runtime_placeholder.markdown(
        f"⏱ **Runtime:** `{runtime:.2f} seconds`",
        unsafe_allow_html=True
    )


# TAB 1 — OVERVIEW & PRICE

with tabs[0]:
    if trades:
        m = calculate_metrics(trades)

        st.markdown("### Strategy Overview")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Trades", m["total_trades"])
        c2.metric("Expectancy (R)", round(m["average_r"], 3))
        c3.metric("Win Rate", f"{m['win_rate']*100:.2f}%")
        c4.metric("Max DD (R)", round(m["max_drawdown_r"], 2))

    chart_df = df.iloc[-min(chart_candles, len(df)):]
    fig = go.Figure(go.Candlestick(
        x=chart_df["datetime"],
        open=chart_df["open"],
        high=chart_df["high"],
        low=chart_df["low"],
        close=chart_df["close"],
        name="Price"
    ))

    fig.update_xaxes(range=[
        chart_df["datetime"].iloc[0],
        chart_df["datetime"].iloc[-1]
    ])

    for t in trades:
        if t.entry_idx < chart_df.index[0]:
            continue
        win = t.r_multiple() > 0
        color = "green" if win else "red"
        direction = str(t.direction).upper()
        symbol = "triangle-up" if direction == "LONG" else "triangle-down"

        fig.add_trace(go.Scatter(
            x=[candles[t.entry_idx]["time"]],
            y=[t.entry_price],
            mode="markers",
            marker=dict(size=11, color=color, symbol=symbol),
            name="Entry"
        ))
        fig.add_trace(go.Scatter(
            x=[candles[t.exit_idx]["time"]],
            y=[t.exit_price],
            mode="markers",
            marker=dict(size=9, color=color, symbol="x"),
            name="Exit"
        ))
        fig.add_trace(go.Scatter(
            x=[candles[t.entry_idx]["time"], candles[t.exit_idx]["time"]],
            y=[t.entry_price, t.exit_price],
            mode="lines",
            line=dict(color=color, width=1),
            showlegend=False
        ))

    fig.update_layout(height=550, hovermode="x unified", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, width="stretch")

    # STREAK ANALYSIS
    if trades:
        win_streak = loss_streak = 0
        max_win = max_loss = 0
        win_start = loss_start = None
        win_range = loss_range = None

        for t in trades:
            r = t.r_multiple()
            if r > 0:
                win_streak += 1
                loss_streak = 0
                win_start = win_start or t.entry_idx
                if win_streak > max_win:
                    max_win = win_streak
                    win_range = (win_start, t.exit_idx)
            else:
                loss_streak += 1
                win_streak = 0
                loss_start = loss_start or t.entry_idx
                if loss_streak > max_loss:
                    max_loss = loss_streak
                    loss_range = (loss_start, t.exit_idx)

        st.markdown("### Streak Analysis")
        c1, c2 = st.columns(2)

        if win_range:
            c1.markdown("🟢 **Longest Winning Streak**")
            c1.metric("Trades", max_win)
            c1.caption(
                f"{candles[win_range[0]]['time']} → {candles[win_range[1]]['time']}"
            )

        if loss_range:
            c2.markdown("🔴 **Longest Losing Streak**")
            c2.metric("Trades", max_loss)
            c2.caption(
                f"{candles[loss_range[0]]['time']} → {candles[loss_range[1]]['time']}"
            )



# TAB 2 — EQUITY & DRAWDOWN

with tabs[1]:
    if trades:
        equity, dd = [], []
        bal, peak = 1.0, 1.0

        for t in trades:
            bal *= (1 + t.r_multiple() * risk_per_trade)
            equity.append((bal - 1) * 100)
            peak = max(peak, bal)
            dd.append((peak - bal) / peak * 100)

        c1, c2 = st.columns(2)
        c1.subheader("Equity Curve (%)")
        c1.line_chart(equity)
        c2.subheader("Drawdown Curve (%)")
        c2.line_chart(dd)



# TAB 3 — TRADE LEDGER

with tabs[2]:
    if trades:
        rows = [{
            "Entry Time": candles[t.entry_idx]["time"],
            "Exit Time": candles[t.exit_idx]["time"],
            "Entry Price": t.entry_price,
            "Exit Price": t.exit_price,
            "R": round(t.r_multiple(), 3),
            "Result": "Win" if t.r_multiple() > 0 else "Loss"
        } for t in trades]
        st.dataframe(pd.DataFrame(rows), width="stretch", height=500)


# TAB 4 — STRATEGY COMPARISON

with tabs[3]:
    if run_bt and strategy_key != "liquidity_sweep":
        rows = []
        for key in StrategyFactory.STRATEGIES:
            if key == "liquidity_sweep":
                continue
            s = StrategyFactory.create(key, candles, {"gaps": gaps})
            tlist = Backtester(candles, gaps, s).run()
            m = calculate_metrics(tlist)
            rows.append({
                "Strategy": key,
                "Trades": m["total_trades"],
                "Expectancy (R)": round(m["average_r"], 3),
                "Win Rate %": round(m["win_rate"] * 100, 2),
                "Max DD (R)": round(m["max_drawdown_r"], 2),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch")
    st.info("Liquidity Sweep excluded — requires structural context.")


# TAB 5 — TIMEFRAME COMPARISON

with tabs[4]:
    if strategy_key == "liquidity_sweep":
        st.info("Liquidity Sweep excluded — requires structural context.")
    elif run_bt:
        rows = []
        for tf in TF_MAP:
            df_tf = load_price_data(tf)
            df_tf = df_tf[
                (df_tf["datetime"] >= range_start) &
                (df_tf["datetime"] <= range_end)
            ]
            if df_tf.empty:
                continue

            candles_tf = [
                {
                    "time": r["datetime"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                }
                for _, r in df_tf.iterrows()
            ]

            _, mins = TF_MAP[tf]
            gaps_tf = detect_gaps(candles_tf, mins)

            s = StrategyFactory.create(strategy_key, candles_tf, {"gaps": gaps_tf})
            tlist = Backtester(candles_tf, gaps_tf, s).run()
            m = calculate_metrics(tlist)

            rows.append({
                "Timeframe": tf,
                "Trades": m["total_trades"],
                "Expectancy (R)": round(m["average_r"], 3),
                "Win Rate %": round(m["win_rate"] * 100, 2),
                "Max DD (R)": round(m["max_drawdown_r"], 2),
            })

        st.dataframe(pd.DataFrame(rows), width="stretch")