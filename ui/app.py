# 
#  Quant Strategy Research Dashboard — v5
#  Fixes: chart zoom, grey boxes removed, use_container_width → width,
#         entry symbol logic, candle visibility, deprecated warnings
# 
import os, sys, time, json
from datetime import date, timedelta, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from loader_enhanced import (
    load_price_data, detect_gaps, resolve_file,
    TF_MINUTES, TF_FILES, WEEKEND_CLOSE, _is_mt5
)
from backtester import Backtester
from strategy_factory import StrategyFactory
from metrics import calculate_metrics
from costs.transaction_costs import InstrumentConfig, get_cost_model
from risk.position_sizer import PositionSizer
from risk.risk_controller import RiskController
from simulation.monte_carlo import MonteCarloSimulator
from optimization.grid_search import GridSearchOptimizer
from validation.walk_forward import WalkForwardTester

pd.set_option("styler.render.max_elements", 2_000_000)

st.set_page_config(
    page_title="Quant Research Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

#  CSS: no grey boxes anywhere, clean dark theme 
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    /* Remove grey box from st.metric entirely */
    div[data-testid="stMetric"] {
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
    }
    div[data-testid="stMetric"] label {
        color: #787b86 !important;
        font-size: 1.1rem !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 500 !important;
        color: #d1d4dc !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
    /* Table styling for detail stats */
    table { width:100%; border-collapse:collapse; font-size:0.85rem; }
    th { color:#787b86; font-weight:500; padding:4px 8px;
         border-bottom:1px solid #2a2e39; text-align:left; }
    td { color:#d1d4dc; padding:5px 8px; border-bottom:1px solid #1e222d; }
    td:first-child { color:#9598a1; }
</style>
""", unsafe_allow_html=True)

DATA_DIR   = os.path.join(ROOT, "data")
RESULTS_DB = os.path.join(ROOT, "results_cache.json")
SYMBOLS    = ["BTCUSD", "XAUUSD", "EURUSD"]
TIMEFRAMES = ["M1", "M5", "M15", "H1", "H2", "H4", "D1", "W1"]

#  TV chart layout 
TV_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#131722",
    plot_bgcolor="#131722",
    font=dict(family="Inter,Arial,sans-serif", color="#787b86", size=12),
    xaxis=dict(
        showgrid=True, gridcolor="#2a2e39", gridwidth=1,
        showline=False, zeroline=False,
        tickfont=dict(color="#9598a1", size=11),
        rangeslider_visible=False,
        spikesnap="cursor", spikemode="across",
        spikethickness=1, spikecolor="#9598a1", spikedash="solid",
        showspikes=True,
    ),
    yaxis=dict(
        showgrid=True, gridcolor="#2a2e39", gridwidth=1,
        showline=False, zeroline=False,
        tickfont=dict(color="#9598a1", size=11),
        spikesnap="cursor", spikemode="across",
        spikethickness=1, spikecolor="#9598a1", spikedash="solid",
        showspikes=True, side="right",
    ),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#1e222d", bordercolor="#2a2e39",
                    font=dict(color="#d1d4dc", size=12)),
    margin=dict(l=10, r=72, t=44, b=32),
    legend=dict(
        bgcolor="rgba(19,23,34,0.85)", bordercolor="#2a2e39", borderwidth=1,
        font=dict(color="#9598a1", size=11),
        x=0.01, y=0.99, xanchor="left", yanchor="top",
    ),
)

# scrollZoom=False prevents the entire browser page from zooming when
# the user pinches/scrolls over the chart in Streamlit's iframe.
# Use box-zoom (drag) or the +/- buttons — both are smooth and accurate.
TV_CONFIG = dict(
    scrollZoom=False,
    displayModeBar=True,
    displaylogo=False,
    modeBarButtonsToRemove=["lasso2d", "autoScale2d"],
    toImageButtonOptions=dict(format="png", scale=2),
    doubleClick="reset+autosize",
)


#  helpers 
def file_available(symbol, tf):
    try:
        resolve_file(DATA_DIR, symbol, tf)
        return True
    except FileNotFoundError:
        return False


@st.cache_data(show_spinner=False)
def _load_df(symbol: str, timeframe: str) -> pd.DataFrame:
    path = resolve_file(DATA_DIR, symbol, timeframe)
    if _is_mt5(path):
        df = pd.read_csv(path, sep="\t")
        df.columns = [c.strip("<>").lower() for c in df.columns]
        if "time" in df.columns:
            df["datetime"] = pd.to_datetime(
                df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M:%S")
            df = df.drop(columns=["time"])
        else:
            df["datetime"] = pd.to_datetime(df["date"], format="%Y.%m.%d")
    else:
        df = pd.read_csv(path)
        tcol = next((c for c in ["datetime","time","timestamp","date"] if c in df.columns), None)
        df["datetime"] = pd.to_datetime(df[tcol])
        if tcol and tcol != "datetime" and tcol in df.columns:
            df = df.drop(columns=[tcol])
    return df.sort_values("datetime").reset_index(drop=True)


def filter_df(df, mode, start_d, end_d, year):
    latest = df["datetime"].max().date()
    if mode == "Last 3 Months":
        df = df[df["datetime"].dt.date >= latest - timedelta(days=90)]
    elif mode == "Last 6 Months":
        df = df[df["datetime"].dt.date >= latest - timedelta(days=180)]
    elif mode == "Last 12 Months":
        df = df[df["datetime"].dt.date >= latest - timedelta(days=365)]
    elif mode == "Year":
        df = df[df["datetime"].dt.year == year]
    elif mode == "Custom":
        df = df[(df["datetime"].dt.date >= start_d) & (df["datetime"].dt.date <= end_d)]
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def _get_candles_and_gaps(symbol, timeframe, range_mode, start_d, end_d, year):
    df = _load_df(symbol, timeframe)
    df = filter_df(df, range_mode, start_d, end_d, year)
    if df.empty:
        return [], set()
    vol_col = "volume" if "volume" in df.columns else (
              "tickvol" if "tickvol" in df.columns else None)
    df2 = df.rename(columns={"datetime": "time"})
    if vol_col and vol_col != "volume":
        df2 = df2.rename(columns={vol_col: "volume"})
    keep = [c for c in ["time","open","high","low","close","volume"] if c in df2.columns]
    df2 = df2[keep]
    if "volume" not in df2.columns:
        df2["volume"] = 0.0
    candles = df2.to_dict("records")
    gaps = detect_gaps(candles, TF_MINUTES.get(timeframe, 15), instrument=symbol)
    return candles, gaps


def run_backtest(symbol, timeframe, strategy_key, cost_model, capital, risk_pct,
                 range_mode, start_d, end_d, year):
    candles, gaps = _get_candles_and_gaps(
        symbol, timeframe, range_mode, start_d, end_d, year)
    if not candles:
        raise ValueError("No candles in selected date range.")
    if strategy_key == "liquidity_sweep":
        raise RuntimeError("Liquidity Sweep needs swing structure; use single-run mode.")
    strategy = StrategyFactory.create(strategy_key, candles, {"gaps": gaps})
    bt = Backtester(candles, gaps, strategy,
                    cost_model=cost_model, capital=capital,
                    risk_pct=risk_pct, instrument=symbol)
    trades  = bt.run()
    metrics = calculate_metrics(trades, initial_capital=capital)
    return trades, candles, gaps, metrics, bt


def fmt_d(v):  return f"${v:+,.2f}"
def fmt_p(v):  return f"{v:.2f}%"
def _parse_dollar(s):
    try:
        return float(str(s).replace("$","").replace(",","").replace("+","").replace("−","-"))
    except Exception:
        return 0.0


#  extended metrics 
def compute_extended_metrics(trades, candles, capital):
    if not trades:
        return {}
    results = []
    for t in trades:
        pnl  = getattr(t, "net_pnl", 0)
        rval = getattr(t, "total_r", 0)
        direction = getattr(t, "direction", "long")
        entry_idx = getattr(t, "entry_idx", None)
        exit_idx  = getattr(t, "exit_idx",  None)
        try:
            et = candles[entry_idx]["time"] if entry_idx is not None else None
            xt = candles[exit_idx]["time"]  if exit_idx  is not None else None
        except Exception:
            et = xt = None
        results.append({"pnl": pnl, "r": rval, "dir": direction, "et": et, "xt": xt})

    # Streaks
    best_streak = worst_streak = 0
    best_start = best_end = worst_start = worst_end = None
    cur_win = cur_loss = 0
    cur_win_start = cur_loss_start = None
    for row in results:
        if row["pnl"] > 0:
            if cur_win == 0: cur_win_start = row["et"]
            cur_win += 1; cur_loss = 0
            if cur_win > best_streak:
                best_streak = cur_win; best_start = cur_win_start; best_end = row["xt"]
        else:
            if cur_loss == 0: cur_loss_start = row["et"]
            cur_loss += 1; cur_win = 0
            if cur_loss > worst_streak:
                worst_streak = cur_loss; worst_start = cur_loss_start; worst_end = row["xt"]

    by_r = sorted(results, key=lambda x: x["r"])
    worst_trade, best_trade = by_r[0], by_r[-1]

    durations = []
    for row in results:
        if row["et"] and row["xt"]:
            try: durations.append((row["xt"] - row["et"]).total_seconds() / 3600)
            except Exception: pass
    avg_dur_h = sum(durations) / len(durations) if durations else 0

    longs  = [r for r in results if r["dir"] == "long"]
    shorts = [r for r in results if r["dir"] == "short"]
    long_wr  = sum(1 for r in longs  if r["pnl"] > 0) / len(longs)  if longs  else 0
    short_wr = sum(1 for r in shorts if r["pnl"] > 0) / len(shorts) if shorts else 0

    win_rs   = [r["r"] for r in results if r["pnl"] > 0]
    loss_rs  = [r["r"] for r in results if r["pnl"] <= 0]
    avg_win_r  = sum(win_rs)  / len(win_rs)  if win_rs  else 0
    avg_loss_r = sum(loss_rs) / len(loss_rs) if loss_rs else 0
    expectancy = sum(r["pnl"] for r in results) / len(results) if results else 0

    all_r  = [r["r"] for r in results]
    mean_r = sum(all_r) / len(all_r) if all_r else 0
    if len(all_r) > 1:
        std_r  = (sum((r - mean_r)**2 for r in all_r) / len(all_r)) ** 0.5
        sharpe = mean_r / std_r if std_r > 0 else 0
    else:
        sharpe = 0

    def ft(t):
        if t is None: return "—"
        try: return t.strftime("%Y-%m-%d %H:%M")
        except: return str(t)

    return {
        "best_streak": best_streak, "best_start": ft(best_start), "best_end": ft(best_end),
        "worst_streak": worst_streak, "worst_start": ft(worst_start), "worst_end": ft(worst_end),
        "best_r": best_trade["r"], "best_pnl": best_trade["pnl"],
        "worst_r": worst_trade["r"], "worst_pnl": worst_trade["pnl"],
        "avg_dur_h": avg_dur_h, "n_longs": len(longs), "n_shorts": len(shorts),
        "long_wr": long_wr, "short_wr": short_wr,
        "avg_win_r": avg_win_r, "avg_loss_r": avg_loss_r,
        "expectancy": expectancy, "sharpe": sharpe,
    }


#  TradingView-quality candlestick chart 
def build_tv_chart(candles, trades, chart_candles, sym, tf):
    n = len(candles)
    # Default view: last 150 candles so individual bars are clearly readable.
    # The user can drag the box-zoom handle or use +/- buttons to see more.
    default_view = min(150, chart_candles)
    start_idx = max(0, n - chart_candles)
    vis = candles[start_idx:]
    df_c = pd.DataFrame(vis)

    chart_start_time = df_c["time"].iloc[0]
    chart_end_time   = df_c["time"].iloc[-1]
    default_x_start  = df_c["time"].iloc[max(0, len(df_c) - default_view)]

    fig = go.Figure()

    #  Candlestick 
    fig.add_trace(go.Candlestick(
        x=df_c["time"],
        open=df_c["open"], high=df_c["high"],
        low=df_c["low"],   close=df_c["close"],
        name="Price",
        increasing=dict(line=dict(color="#26a69a", width=1), fillcolor="#26a69a"),
        decreasing=dict(line=dict(color="#ef5350", width=1), fillcolor="#ef5350"),
        whiskerwidth=0,
        showlegend=False,
        hoverinfo="x+y",
    ))

    #  Trade overlays 
    entry_x_win=[]; entry_y_win=[]; entry_t_win=[]; entry_s_win=[]
    entry_x_los=[]; entry_y_los=[]; entry_t_los=[]; entry_s_los=[]
    exit_x=[]; exit_y=[]; exit_colors=[]; exit_texts=[]

    for t in trades:
        try:
            et = candles[t.entry_idx]["time"]
            xt = candles[t.exit_idx]["time"] if t.exit_idx is not None else None
        except Exception:
            continue
        if et > chart_end_time or (xt and xt < chart_start_time):
            continue
        if et < chart_start_time:
            continue

        pnl  = getattr(t, "net_pnl", 0)
        rval = getattr(t, "total_r", 0)
        win  = pnl > 0
        lc   = "#26a69a" if win else "#ef5350"
        dir_str = "LONG ▲" if t.direction == "long" else "SHORT ▼"
        tip = (f"{dir_str}  {'✅ WIN' if win else '❌ LOSS'}<br>"
               f"R: {rval:+.2f}   P&L: ${pnl:+,.2f}<br>"
               f"Entry: {t.entry_price:.5f}  →  "
               f"Exit: {f'{t.exit_price:.5f}' if t.exit_price else 'open'}<br>"
               f"SL: {t.sl:.5f}   TP: {t.tp:.5f}")

        # Connecting line entry→exit
        if xt and t.exit_price:
            fig.add_trace(go.Scatter(
                x=[et, xt], y=[t.entry_price, t.exit_price],
                mode="lines",
                line=dict(color=lc, width=1.5),
                showlegend=False, hoverinfo="skip", opacity=0.65,
            ))
            exit_x.append(xt)
            exit_y.append(t.exit_price)
            exit_colors.append(lc)
            exit_texts.append(tip)

        # Triangle direction: up=long, down=short
        esym = "triangle-up" if t.direction == "long" else "triangle-down"
        if win:
            entry_x_win.append(et); entry_y_win.append(t.entry_price)
            entry_t_win.append(tip); entry_s_win.append(esym)
        else:
            entry_x_los.append(et); entry_y_los.append(t.entry_price)
            entry_t_los.append(tip); entry_s_los.append(esym)

    # Winning entries — green triangles
    if entry_x_win:
        fig.add_trace(go.Scatter(
            x=entry_x_win, y=entry_y_win,
            mode="markers", name="Win Entry",
            marker=dict(symbol=entry_s_win, size=10, color="#26a69a",
                        line=dict(color="#0d1117", width=1)),
            text=entry_t_win, hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ))

    # Losing entries — red triangles
    if entry_x_los:
        fig.add_trace(go.Scatter(
            x=entry_x_los, y=entry_y_los,
            mode="markers", name="Loss Entry",
            marker=dict(symbol=entry_s_los, size=10, color="#ef5350",
                        line=dict(color="#0d1117", width=1)),
            text=entry_t_los, hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ))

    # Exit dots
    if exit_x:
        fig.add_trace(go.Scatter(
            x=exit_x, y=exit_y,
            mode="markers", name="Exit",
            marker=dict(symbol="circle", size=7, color=exit_colors,
                        line=dict(color="#131722", width=1)),
            text=exit_texts, hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ))

    layout = {**TV_LAYOUT}
    layout["height"] = 640
    layout["title"] = dict(
        text=f"<b>{sym}</b>  ·  {tf}",
        font=dict(color="#d1d4dc", size=14),
        x=0.01, xanchor="left",
    )
    layout["xaxis"] = {
        **TV_LAYOUT["xaxis"],
        "rangeslider_visible": False,
        "autorange": False,
        "fixedrange": False,
        # Show only last `default_view` candles on load — readable without zooming
        "range": [default_x_start, chart_end_time],
    }
    layout["yaxis"] = {
        **TV_LAYOUT["yaxis"],
        "autorange": True,
        "fixedrange": False,
    }
    fig.update_layout(**layout)
    return fig


#  results cache 
@st.cache_data(show_spinner=False)
def load_results_cache():
    if not os.path.exists(RESULTS_DB):
        return {}
    with open(RESULTS_DB) as f:
        return json.load(f)

def cache_key(symbol, tf, strategy, costs_on):
    return f"{symbol}|{tf}|{strategy}|{'costs' if costs_on else 'nocosts'}"


#  sidebar 
with st.sidebar:
    st.markdown("## ⚙️ Backtest Settings")
    st.divider()
    symbol = st.selectbox("🪙 Instrument", SYMBOLS)
    avail_tfs = [tf for tf in TIMEFRAMES if file_available(symbol, tf)]
    if not avail_tfs:
        st.warning(f"No data files for {symbol} in {DATA_DIR}")
        avail_tfs = TIMEFRAMES
    timeframe = st.selectbox("⏱ Timeframe", avail_tfs)
    st.divider()
    strategy_key = st.selectbox("📐 Strategy", list(StrategyFactory.STRATEGIES.keys()))
    st.divider()
    st.markdown("**💰 Cost Model**")
    inst_cfg = InstrumentConfig.get(symbol)
    st.caption(inst_cfg["description"])
    use_costs = st.toggle("Enable Transaction Costs", value=True)
    st.divider()
    st.markdown("**📊 Position Sizing**")
    capital  = st.number_input("Initial Capital ($)", 1000, 1_000_000,
                                inst_cfg.get("default_capital", 10000), step=1000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0, 0.1) / 100
    st.divider()
    st.markdown("**🛡 Risk Controller**")
    max_dd_limit    = st.slider("Max Drawdown Limit (%)", 5, 50, 20) / 100
    max_daily_loss  = st.slider("Max Daily Loss (%)", 1, 10, 2) / 100
    max_consec_loss = st.slider("Max Consecutive Losses", 2, 10, 5)
    st.divider()
    st.markdown("**📅 Date Range**")
    range_mode = st.selectbox("Range", [
        "Full History","Last 3 Months","Last 6 Months",
        "Last 12 Months","Year","Custom"
    ])
    start_d = end_d = year = None
    if range_mode == "Year":
        year = st.selectbox("Year", list(range(2018, 2027))[::-1])
    elif range_mode == "Custom":
        start_d = st.date_input("Start", date(2020, 1, 1))
        end_d   = st.date_input("End",   date(2025, 12, 31))
    st.divider()
    chart_candles = st.slider("Chart visible candles", 100, 5000, 500, 100)
    cache = load_results_cache()
    ck = cache_key(symbol, timeframe, strategy_key, use_costs)
    cache_hit = ck in cache
    if cache_hit:
        st.success("✅ Pre-computed result available")
    else:
        st.info("💡 Run `python run_all_tests.py` to pre-compute all results")
    run_btn   = st.button("▶️  Run Backtest", type="primary", use_container_width=True)
    status_ph = st.empty()


#  title 
st.markdown("# 📈 Quant Strategy Research Dashboard")
st.caption(
    f"**{symbol}** | **{timeframe}** | **{strategy_key}** | "
    f"Costs: **{'ON' if use_costs else 'OFF'}** | "
    f"Capital: **${capital:,}** | Risk: **{risk_pct*100:.1f}%**"
)

tabs = st.tabs([
    "📊 Overview", "💹 Equity & DD", "📋 Trade Ledger",
    "💸 Cost Analysis", "🔀 Instrument Comparison", "⏱ Timeframe Comparison",
    "🔍 Grid Search", "🎲 Monte Carlo", "🔄 Walk-Forward",
    "🛡 Risk Controller", "📦 All Results",
])

for k, v in [("trades",[]),("candles",[]),("gaps",set()),
              ("metrics",{}),("bt",None),("sym",symbol),("tf",timeframe)]:
    if k not in st.session_state:
        st.session_state[k] = v


#  run backtest 
if run_btn:
    if cache_hit and range_mode == "Full History":
        cached_r = cache[ck]
        status_ph.success(
            f"⚡ Cache hit — {cached_r.get('total_trades','?')} trades | "
            f"Avg R: {cached_r.get('average_r',0):.3f} | "
            f"Net P&L: {cached_r.get('net_pnl',0):+,.2f}"
        )
    with st.spinner("Running backtest…"):
        t0 = time.perf_counter()
        try:
            cm = get_cost_model(symbol) if use_costs else None
            trades, candles, gaps, metrics, bt = run_backtest(
                symbol, timeframe, strategy_key, cm, capital, risk_pct,
                range_mode, start_d, end_d, year
            )
            st.session_state.update(dict(
                trades=trades, candles=candles, gaps=gaps,
                metrics=metrics, bt=bt, sym=symbol, tf=timeframe
            ))
            elapsed = time.perf_counter() - t0
            status_ph.success(
                f"✅ {len(candles):,} candles | {len(gaps)} gaps | "
                f"{len(trades)} trades | {elapsed:.2f}s"
                + (" (candles cached)" if cache_hit else "")
            )
        except RuntimeError as e:
            st.warning(f"⚠️ {e}")
        except Exception as e:
            import traceback
            st.error(f"Error: {e}")
            st.code(traceback.format_exc())

trades  = st.session_state.trades
candles = st.session_state.candles
gaps    = st.session_state.gaps
metrics = st.session_state.metrics


# ═══════════════════════════════════════════════════════════════════
# TAB 1: Overview
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:
    if not trades:
        st.info("Configure settings and click **▶️ Run Backtest**.")
    else:
        m  = metrics
        ex = compute_extended_metrics(trades, candles, capital)

        
        c1,c2,c3,c4,c5 = st.columns(5)

        c1.metric("Trades",        f"{m['total_trades']:,}")
        c2.metric("Win Rate",      fmt_p(m["win_rate"]*100))
        c3.metric("Net P&L",       f"${m['net_pnl']:+,.2f}",
                delta=fmt_p(m["return_pct"]))
        c4.metric("Max DD",        fmt_p(m["max_drawdown_pct"]*100))
        # c5.metric("Total R",       f"{m['total_r']:.2f}R")
        c5.metric("Avg R / Trade", f"{m['average_r']:+.3f}R")

        st.divider()

        
        fig = build_tv_chart(
            candles, trades, chart_candles,
            st.session_state.sym, st.session_state.tf
        )
        st.plotly_chart(fig, width="stretch", config=TV_CONFIG)

        st.divider()

        #  Detailed stats — clean HTML tables, no grey boxes 
        st.markdown("#### 📊 Detailed Statistics")

        def _g(v): return f'<span style="color:#26a69a;font-weight:600">{v}</span>'
        def _r(v): return f'<span style="color:#ef5350;font-weight:600">{v}</span>'
        def _w(v): return f'<span style="color:#d1d4dc;font-weight:600">{v}</span>'

        cost_ratio = abs(m['total_costs'] / m['gross_pnl'] * 100) if m.get('gross_pnl') else 0

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            st.markdown("**📈 Streak Analysis**")
            st.markdown(f"""
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>🏆 Best Win Streak</td><td>{_g(f"{ex['best_streak']} trades")}</td></tr>
<tr><td>Win Period Start</td><td>{_g(ex['best_start'])}</td></tr>
<tr><td>Win Period End</td><td>{_g(ex['best_end'])}</td></tr>
<tr><td>💀 Worst Loss Streak</td><td>{_r(f"{ex['worst_streak']} trades")}</td></tr>
<tr><td>Loss Period Start</td><td>{_r(ex['worst_start'])}</td></tr>
<tr><td>Loss Period End</td><td>{_r(ex['worst_end'])}</td></tr>
</table>
""", unsafe_allow_html=True)

        with col_b:
            st.markdown("**🎯 Trade Performance**")
            st.markdown(f"""
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>🥇 Best Trade</td><td>{_g(f"{ex['best_r']:+.2f}R / ${ex['best_pnl']:+,.2f}")}</td></tr>
<tr><td>💣 Worst Trade</td><td>{_r(f"{ex['worst_r']:+.2f}R / ${ex['worst_pnl']:+,.2f}")}</td></tr>
<tr><td>📈 Avg Winner</td><td>{_g(f"{ex['avg_win_r']:+.3f}R")}</td></tr>
<tr><td>📉 Avg Loser</td><td>{_r(f"{ex['avg_loss_r']:+.3f}R")}</td></tr>
<tr><td>⏱ Avg Duration</td><td>{_w(f"{ex['avg_dur_h']:.1f}h")}</td></tr>
<tr><td>💵 Expectancy</td><td>{(_g if ex['expectancy']>=0 else _r)(fmt_d(ex['expectancy']))}</td></tr>
</table>
""", unsafe_allow_html=True)

        with col_c:
            st.markdown("**🔀 Long vs Short**")
            lwr = ex['long_wr']*100; swr = ex['short_wr']*100
            st.markdown(f"""
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>🟢 Long Trades</td><td>{_w(str(ex['n_longs']))} — {(_g if ex['long_wr']>0.4 else _r)(f"{lwr:.1f}% WR")}</td></tr>
<tr><td>🔴 Short Trades</td><td>{_w(str(ex['n_shorts']))} — {(_g if ex['short_wr']>0.4 else _r)(f"{swr:.1f}% WR")}</td></tr>
<tr><td>✅ Total Wins</td><td>{_g(str(m['wins']))}</td></tr>
<tr><td>❌ Total Losses</td><td>{_r(str(m['losses']))}</td></tr>
<tr><td>➖ Breakevens</td><td>{_w(str(m.get('breakevens',0)))}</td></tr>
<tr><td>📊 Profit Factor</td><td>{(_g if m['profit_factor']>=1 else _r)(f"{m['profit_factor']:.2f}")}</td></tr>
</table>
""", unsafe_allow_html=True)

        with col_d:
            st.markdown("**💸 Cost Impact**")
            st.markdown(f"""
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Gross P&L</td><td>{(_g if m['gross_pnl']>=0 else _r)(fmt_d(m['gross_pnl']))}</td></tr>
<tr><td>Total Costs</td><td>{_r(fmt_d(-abs(m['total_costs'])))}</td></tr>
<tr><td>Net P&L</td><td>{(_g if m['net_pnl']>=0 else _r)(fmt_d(m['net_pnl']))}</td></tr>
<tr><td>Cost Drag</td><td>{_r(f"{cost_ratio:.1f}%")} of gross</td></tr>
<tr><td>Max Drawdown</td><td>{_r(fmt_p(m['max_drawdown_pct']*100))}</td></tr>
<tr><td>Return</td><td>{(_g if m['return_pct']>=0 else _r)(fmt_p(m['return_pct']))}</td></tr>
</table>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 2: Equity & DD
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    if not trades:
        st.info("Run a backtest first.")
    else:
        eq = [capital]; ts = []
        try:    ts = [candles[0]["time"]]
        except: ts = [datetime.now()]
        for t in trades:
            try:    ts.append(candles[t.exit_idx]["time"] if t.exit_idx is not None else ts[-1])
            except: ts.append(ts[-1])
            eq.append(eq[-1] + getattr(t, "net_pnl", 0))

        eq_s = pd.Series(eq, index=ts)
        peak = eq_s.cummax()
        dd_s = (peak - eq_s) / peak * 100
        dd_s = dd_s.fillna(0)

        fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             row_heights=[0.65, 0.35], vertical_spacing=0.04)

        fig2.add_trace(go.Scatter(
            x=eq_s.index, y=eq_s.values,
            fill="tozeroy", fillcolor="rgba(38,166,154,0.08)",
            name="Equity", line=dict(color="#26a69a", width=2)
        ), row=1, col=1)
        fig2.add_hline(y=capital, line_dash="dot", line_color="#787b86",
                       annotation_text=f"Start ${capital:,}",
                       annotation_font_color="#787b86", row=1, col=1)

        peak_val = eq_s.max(); peak_idx = eq_s.idxmax()
        fig2.add_trace(go.Scatter(
            x=[peak_idx], y=[peak_val], mode="markers+text",
            marker=dict(size=8, color="#f6c90e"),
            text=[f"Peak ${peak_val:,.0f}"],
            textposition="top right", textfont=dict(color="#f6c90e", size=10),
            showlegend=False
        ), row=1, col=1)

        fig2.add_trace(go.Scatter(
            x=dd_s.index, y=-dd_s.values,
            fill="tozeroy", fillcolor="rgba(239,83,80,0.15)",
            name="Drawdown %", line=dict(color="#ef5350", width=1)
        ), row=2, col=1)

        max_dd_val = dd_s.max(); max_dd_idx = dd_s.idxmax()
        fig2.add_trace(go.Scatter(
            x=[max_dd_idx], y=[-max_dd_val], mode="markers+text",
            marker=dict(size=8, color="#ef5350", symbol="x"),
            text=[f"Max {max_dd_val:.1f}%"],
            textposition="bottom right", textfont=dict(color="#ef5350", size=10),
            showlegend=False
        ), row=2, col=1)

        layout2 = {**TV_LAYOUT, "height": 580, "hovermode": "x unified"}
        layout2["yaxis"]  = {**TV_LAYOUT["yaxis"], "title": "Equity ($)"}
        layout2["yaxis2"] = {**TV_LAYOUT["yaxis"], "title": "Drawdown (%)"}
        fig2.update_layout(**layout2)
        st.plotly_chart(fig2, width="stretch", config=TV_CONFIG)

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Final Capital",  f"${metrics['final_capital']:,.2f}")
        c2.metric("Return",          fmt_p(metrics["return_pct"]))
        c3.metric("Max Drawdown",    fmt_p(metrics["max_drawdown_pct"]*100))
        c4.metric("Profit Factor",   f"{metrics['profit_factor']:.2f}")
        c5.metric("Total R",         f"{metrics['total_r']:.2f}R")
        c6.metric("Avg R / Trade",   f"{metrics['average_r']:.3f}R")


# ═══════════════════════════════════════════════════════════════════
# TAB 3: Trade Ledger
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    if not trades:
        st.info("Run a backtest first.")
    else:
        MAX_DISPLAY = 10000
        display_trades = trades[:MAX_DISPLAY]
        if len(trades) > MAX_DISPLAY:
            st.warning(f"Showing first {MAX_DISPLAY:,} of {len(trades):,}. Download CSV for full list.")
        rows = []
        for i, t in enumerate(display_trades):
            try:
                et = str(candles[t.entry_idx]["time"])
                xt = str(candles[t.exit_idx]["time"]) if t.exit_idx is not None else ""
            except Exception:
                et = xt = ""
            rows.append({
                "#": i+1, "Dir": t.direction.upper(),
                "Entry Time": et, "Exit Time": xt,
                "Entry":  round(t.entry_price, 5),
                "Exit":   round(t.exit_price, 5) if t.exit_price else "",
                "Size":   round(getattr(t,"size",1.0), 4),
                "SL":     round(t.sl, 5) if t.sl else "",
                "TP":     round(t.tp, 5) if t.tp else "",
                "Gross":  round(getattr(t,"gross_pnl",0), 2),
                "Costs":  round(getattr(t,"total_costs",0), 2),
                "Net":    round(getattr(t,"net_pnl",0), 2),
                "R":      round(getattr(t,"total_r",0), 2),
                "Result": str(getattr(t,"result","")),
            })
        df_led = pd.DataFrame(rows)
        def color_pnl(val):
            try:
                v = float(val)
                return f"color: {'#26a69a' if v>0 else '#ef5350' if v<0 else '#888'}"
            except Exception:
                return ""
        styled = df_led.style.map(color_pnl, subset=["Net","Gross","R"])
        st.dataframe(styled, width="stretch", height=450)
        st.download_button("⬇️ Download Full CSV",
            df_led.to_csv(index=False),
            f"trades_{symbol}_{timeframe}.csv", "text/csv")


# ═══════════════════════════════════════════════════════════════════
# TAB 4: Cost Analysis
# ═══════════════════════════════════════════════════════════════════
with tabs[3]:
    if not trades:
        st.info("Run a backtest first.")
    elif not use_costs:
        st.info("Enable Transaction Costs in the sidebar.")
    else:
        m = metrics
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Costs",    fmt_d(m["total_costs"]))
        c2.metric("Gross P&L",      fmt_d(m["gross_pnl"]))
        c3.metric("Net P&L",        fmt_d(m["net_pnl"]))
        avg_cost = m["total_costs"]/m["total_trades"] if m["total_trades"] else 0
        c4.metric("Avg Cost/Trade", fmt_d(avg_cost))

        CHART_N = min(len(trades), 500)
        tnums = list(range(1, CHART_N+1))
        gross = [getattr(t,"gross_pnl",0) for t in trades[:CHART_N]]
        net   = [getattr(t,"net_pnl",0)   for t in trades[:CHART_N]]
        costs_l = [getattr(t,"total_costs",0) for t in trades[:CHART_N]]

        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=tnums, y=gross, name="Gross", marker_color="#42a5f5", opacity=0.7))
        fig3.add_trace(go.Bar(x=tnums, y=net,   name="Net",   marker_color="#26a69a", opacity=0.9))
        fig3.add_trace(go.Scatter(x=tnums, y=[-c for c in costs_l],
            mode="lines", name="Cost (neg)", line=dict(color="#ef5350", width=1)))
        layout3 = {**TV_LAYOUT, "height": 360, "barmode": "overlay",
                   "title": dict(text=f"Gross vs Net P&L (first {CHART_N} trades)",
                                 font=dict(color="#d1d4dc",size=13), x=0.01)}
        fig3.update_layout(**layout3)
        st.plotly_chart(fig3, width="stretch", config=TV_CONFIG)

        col1,col2 = st.columns(2)
        cm_obj = inst_cfg["cost_model"]
        with col1:
            st.markdown(f"**Spread:** `${cm_obj.spread_cost:.6f}/unit`")
            st.markdown(f"**Commission:** `${cm_obj.commission_per_lot:.6f}/unit`")
            st.markdown(f"**Slippage:** `${cm_obj.slippage_cost:.6f}/unit`")
        with col2:
            cost_drag = abs(m["total_costs"]/m["gross_pnl"]*100) if m.get("gross_pnl") else 0
            st.metric("Cost Drag on Gross", fmt_p(cost_drag))


# ═══════════════════════════════════════════════════════════════════
# TAB 5: Instrument Comparison
# ═══════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("### Same Strategy — All Instruments")
    tf_cmp = st.selectbox("Timeframe",
        [tf for tf in TIMEFRAMES if any(file_available(s,tf) for s in SYMBOLS)],
        key="instr_tf")
    if st.button("▶️ Run Instrument Comparison", key="run_instr"):
        results = []
        for sym in SYMBOLS:
            try:
                cm_s = get_cost_model(sym) if use_costs else None
                t_s,c_s,g_s,m_s,_ = run_backtest(
                    sym, tf_cmp, strategy_key, cm_s, capital, risk_pct,
                    range_mode, start_d, end_d, year)
                results.append({
                    "Symbol": sym, "Trades": m_s["total_trades"],
                    "Win Rate": fmt_p(m_s["win_rate"]*100),
                    "Net P&L": fmt_d(m_s["net_pnl"]),
                    "Total Costs": fmt_d(m_s["total_costs"]),
                    "Max DD": fmt_p(m_s["max_drawdown_pct"]*100),
                    "Return": fmt_p(m_s["return_pct"]),
                    "Profit Factor": f"{m_s['profit_factor']:.2f}",
                    "Avg R": f"{m_s['average_r']:.3f}",
                })
            except Exception as e:
                results.append({"Symbol": sym, "Trades": 0,
                    "Win Rate":"","Net P&L":str(e)[:60],
                    "Total Costs":"","Max DD":"","Return":"","Profit Factor":"","Avg R":""})
        st.dataframe(pd.DataFrame(results), width="stretch")


# ═══════════════════════════════════════════════════════════════════
# TAB 6: Timeframe Comparison
# ═══════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown("### Same Strategy — All Timeframes")
    sym_cmp = st.selectbox("Instrument", SYMBOLS, key="tf_sym")
    tf_list = [tf for tf in TIMEFRAMES if file_available(sym_cmp, tf)]
    if st.button("▶️ Run Timeframe Comparison", key="run_tf"):
        results = []
        for tf in tf_list:
            try:
                cm_t = get_cost_model(sym_cmp) if use_costs else None
                t_t,c_t,g_t,m_t,_ = run_backtest(
                    sym_cmp, tf, strategy_key, cm_t, capital, risk_pct,
                    range_mode, start_d, end_d, year)
                results.append({
                    "Timeframe": tf, "Candles": len(c_t),
                    "Trades": m_t["total_trades"],
                    "Win Rate": fmt_p(m_t["win_rate"]*100),
                    "Net P&L": fmt_d(m_t["net_pnl"]),
                    "Max DD": fmt_p(m_t["max_drawdown_pct"]*100),
                    "Return": fmt_p(m_t["return_pct"]),
                    "Profit Factor": f"{m_t['profit_factor']:.2f}",
                    "Avg R": f"{m_t['average_r']:.3f}",
                })
            except Exception as e:
                results.append({"Timeframe":tf,"Candles":0,"Trades":0,
                    "Win Rate":"","Net P&L":str(e)[:60],"Max DD":"",
                    "Return":"","Profit Factor":"","Avg R":""})
        if results:
            st.dataframe(pd.DataFrame(results), width="stretch")
            valid = [r for r in results if isinstance(r["Trades"],int) and r["Trades"]>0]
            if valid:
                net_vals = [_parse_dollar(r["Net P&L"]) for r in valid]
                fig_tf = go.Figure(go.Bar(
                    x=[r["Timeframe"] for r in valid], y=net_vals,
                    marker_color=["#26a69a" if v>0 else "#ef5350" for v in net_vals]
                ))
                layout_tf = {**TV_LAYOUT, "height": 300,
                             "title": dict(text="Net P&L by Timeframe",
                                           font=dict(color="#d1d4dc"), x=0.01)}
                fig_tf.update_layout(**layout_tf)
                st.plotly_chart(fig_tf, width="stretch", config=TV_CONFIG)


# ═══════════════════════════════════════════════════════════════════
# TAB 7: Grid Search
# ═══════════════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown("### 🔍 Grid Search — TrendPullbackV3 Only")
    col1,col2 = st.columns(2)
    with col1:
        gs_metric    = st.selectbox("Optimize for",["average_r","total_r","win_rate"],key="gs_m")
        gs_mintrades = st.slider("Min trades",10,200,30,key="gs_mt")
    with col2:
        gs_lookbacks = st.multiselect("Lookback values",[50,100,200,300],default=[100,200])
        gs_min_rrs   = st.multiselect("Min R:R values",[1.5,2.0,2.5,3.0],default=[2.0,2.5])
        gs_atr_mults = st.multiselect("ATR SL mult",[1.0,1.5,2.0,2.5],default=[1.5,2.0])
    if st.button("▶️ Run Grid Search", key="run_gs"):
        if not gs_lookbacks or not gs_min_rrs or not gs_atr_mults:
            st.warning("Select at least one value per parameter.")
        else:
            with st.spinner("Running grid search…"):
                try:
                    from strategies.trend_pullback_v3 import TrendPullbackV3
                    cm_gs = get_cost_model(symbol) if use_costs else None
                    candles_gs, gaps_gs = _get_candles_and_gaps(
                        symbol, timeframe, range_mode, start_d, end_d, year)
                    optimizer = GridSearchOptimizer(metric=gs_metric, min_trades=gs_mintrades)
                    results   = optimizer.optimize(
                        strategy_class=TrendPullbackV3,
                        candles=candles_gs,
                        param_grid={
                            "lookback": gs_lookbacks,
                            "min_rr":   gs_min_rrs,
                            "atr_multiplier_sl": gs_atr_mults,
                        },
                        gaps=gaps_gs, cost_model=cm_gs,
                        instrument=symbol, verbose=False
                    )
                    if not results:
                        st.warning("No valid results — reduce min_trades or add more parameter values.")
                    else:
                        rows_gs = [{
                            "lookback": r["params"].get("lookback",""),
                            "min_rr":   r["params"].get("min_rr",""),
                            "atr_sl":   r["params"].get("atr_multiplier_sl",""),
                            "Trades":   r["total_trades"],
                            "Avg R":    round(r["average_r"],3),
                            "Total R":  round(r["total_r"],2),
                            "Win Rate": fmt_p(r["win_rate"]*100),
                            "Max DD(R)":round(r["max_dd"],2),
                        } for r in results[:20]]
                        st.success(f"✅ {len(results)} valid combos. Top 20:")
                        st.dataframe(pd.DataFrame(rows_gs), width="stretch")
                        best = results[0]["params"]
                        st.info(f"🏆 Best: lookback={best['lookback']}, "
                                f"min_rr={best['min_rr']}, "
                                f"atr_sl={best.get('atr_multiplier_sl','')}")
                except Exception as e:
                    import traceback
                    st.error(f"Grid search error: {e}")
                    st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════
# TAB 8: Monte Carlo
# ═══════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown("### 🎲 Monte Carlo Simulation")
    col1,col2 = st.columns(2)
    with col1:
        mc_sims    = st.number_input("Simulations",1000,50000,10000,1000,key="mc_n")
        mc_risk    = st.slider("Risk per trade (%)",0.1,5.0,float(risk_pct*100),0.1,key="mc_r")/100
    with col2:
        mc_capital = st.number_input("Capital ($)",1000,1_000_000,capital,1000,key="mc_cap")
    if st.button("▶️ Run Monte Carlo", key="run_mc"):
        if not trades:
            st.warning("Run a backtest first.")
        else:
            with st.spinner(f"Running {mc_sims:,} simulations…"):
                try:
                    simulator = MonteCarloSimulator(n_simulations=int(mc_sims))
                    stats     = simulator.simulate(trades, float(mc_capital),
                                                   risk_per_trade=float(mc_risk),
                                                   verbose=False)
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Risk of Ruin",    fmt_p(stats["risk"]["risk_of_ruin"]))
                    c2.metric("Prob Profitable", fmt_p(stats["risk"]["prob_profitable"]))
                    c3.metric("Median Return",   fmt_p(stats["returns"]["median"]))
                    c4.metric("Median Max DD",   fmt_p(stats["drawdowns"]["median"]))
                    st.divider()
                    col1,col2 = st.columns(2)
                    with col1:
                        fe = stats["final_equity"]
                        st.markdown("**Final Equity Percentiles**")
                        for lbl,k in [("P5","p5"),("P25","p25"),("Median","median"),
                                      ("P75","p75"),("P95","p95")]:
                            st.markdown(f"- {lbl}: `${fe[k]:,.2f}`")
                    with col2:
                        r = stats["risk"]
                        st.markdown("**Drawdown Probabilities**")
                        st.markdown(f"- P(DD>20%): `{r['prob_dd_gt_20pct']:.1f}%`")
                        st.markdown(f"- P(DD>30%): `{r['prob_dd_gt_30pct']:.1f}%`")
                        st.markdown(f"- P(DD>50%): `{r['prob_dd_gt_50pct']:.1f}%`")
                    returns_data = [rr["return_pct"] for rr in simulator.results]
                    fig_mc = go.Figure(go.Histogram(x=returns_data,nbinsx=80,
                        marker_color="#42a5f5",opacity=0.8))
                    fig_mc.add_vline(x=0,line_color="#d1d4dc",line_dash="dash")
                    fig_mc.add_vline(x=stats["returns"]["p5"],line_color="#ef5350",
                        line_dash="dot",annotation_text="P5",
                        annotation_font_color="#ef5350")
                    fig_mc.add_vline(x=stats["returns"]["p95"],line_color="#26a69a",
                        line_dash="dot",annotation_text="P95",
                        annotation_font_color="#26a69a")
                    layout_mc = {**TV_LAYOUT, "height": 360,
                                 "title": dict(text=f"Return Distribution ({mc_sims:,} sims)",
                                               font=dict(color="#d1d4dc"), x=0.01),
                                 "xaxis": {**TV_LAYOUT["xaxis"],
                                           "title": "Return %", "showspikes": False},
                                 "yaxis": {**TV_LAYOUT["yaxis"],
                                           "title": "Frequency",
                                           "showspikes": False, "side": "left"}}
                    fig_mc.update_layout(**layout_mc)
                    st.plotly_chart(fig_mc, width="stretch", config=TV_CONFIG)
                except Exception as e:
                    import traceback
                    st.error(f"Monte Carlo error: {e}")
                    st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════
# TAB 9: Walk-Forward
# ═══════════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown("### 🔄 Walk-Forward Validation")
    col1,col2 = st.columns(2)
    with col1:
        wf_in  = st.slider("In-sample months",3,24,12,key="wf_in")
        wf_out = st.slider("Out-of-sample months",1,6,3,key="wf_out")
    with col2:
        wf_mt = st.slider("Min trades per window",5,50,15,key="wf_mt")
    if st.button("▶️ Run Walk-Forward", key="run_wf"):
        with st.spinner("Running walk-forward…"):
            try:
                from strategies.trend_pullback_v3 import TrendPullbackV3
                cm_wf = get_cost_model(symbol) if use_costs else None
                candles_wf, gaps_wf = _get_candles_and_gaps(
                    symbol, timeframe, range_mode, start_d, end_d, year)
                wf = WalkForwardTester(in_sample_periods=wf_in,
                                       out_sample_periods=wf_out,
                                       period_type="months",
                                       min_trades_per_window=wf_mt)
                wf_res = wf.run_walk_forward(
                    strategy_class=TrendPullbackV3,
                    candles=candles_wf,
                    param_grid={"lookback":[100,200],"min_rr":[2.0,2.5]},
                    gaps=gaps_wf, cost_model=cm_wf,
                    instrument=symbol, verbose=False
                )
                summary = wf_res["summary"]
                windows = wf_res["windows"]
                if not windows:
                    st.warning("Not enough data. Use Full History or longer range.")
                else:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Windows",          summary["total_windows"])
                    c2.metric("In-Sample Avg R",  f"{summary['in_sample_avg_r_mean']:.3f}")
                    c3.metric("Out-Sample Avg R", f"{summary['out_sample_avg_r_mean']:.3f}")
                    c4.metric("Degradation",      fmt_p(summary["degradation_pct"]))
                    wf_rows = [{
                        "Win":         w["window"],
                        "In Start":    str(w["in_sample_period"][0].date()),
                        "In End":      str(w["in_sample_period"][1].date()),
                        "Out Start":   str(w["out_sample_period"][0].date()),
                        "Out End":     str(w["out_sample_period"][1].date()),
                        "Best Params": str(w["best_params"]),
                        "In Avg R":    round(w["in_sample_metrics"]["average_r"],3),
                        "Out Avg R":   round(w["out_sample_metrics"]["average_r"],3),
                        "Degrad.":     round(w["degradation"],3),
                    } for w in windows]
                    st.dataframe(pd.DataFrame(wf_rows), width="stretch")
                    wns = [w["window"] for w in windows]
                    fig_wf = go.Figure()
                    fig_wf.add_trace(go.Bar(x=wns,
                        y=[w["in_sample_metrics"]["average_r"] for w in windows],
                        name="In-Sample Avg R", marker_color="#42a5f5"))
                    fig_wf.add_trace(go.Bar(x=wns,
                        y=[w["out_sample_metrics"]["average_r"] for w in windows],
                        name="Out-Sample Avg R", marker_color="#26a69a"))
                    fig_wf.add_hline(y=0, line_color="#787b86", line_dash="dash")
                    layout_wf = {**TV_LAYOUT, "height": 320, "barmode": "group",
                                 "title": dict(text="In vs Out-of-Sample Avg R",
                                               font=dict(color="#d1d4dc"), x=0.01)}
                    fig_wf.update_layout(**layout_wf)
                    st.plotly_chart(fig_wf, width="stretch", config=TV_CONFIG)
            except Exception as e:
                import traceback
                st.error(f"Walk-forward error: {e}")
                st.code(traceback.format_exc())


# ═══════════════════════════════════════════════════════════════════
# TAB 10: Risk Controller
# ═══════════════════════════════════════════════════════════════════
with tabs[9]:
    st.markdown("### 🛡 Risk Controller — Backtest Replay")
    if not trades:
        st.info("Run a backtest first.")
    else:
        rc = RiskController(
            initial_capital=capital,
            max_daily_loss_pct=max_daily_loss,
            max_weekly_loss_pct=max_daily_loss*2.5,
            max_drawdown_pct=max_dd_limit,
            max_consecutive_losses=max_consec_loss,
        )
        equity_now = capital; halted_at = []; trades_so_far = []
        for t in trades:
            try:    trade_time = candles[t.entry_idx]["time"]
            except: trade_time = None
            t.trade_time = trade_time
            if trade_time:
                can, reason = rc.can_trade(equity_now, trade_time, trades_so_far)
                if not can:
                    halted_at.append({
                        "Trade #": trades.index(t)+1,
                        "Reason":  reason,
                        "Equity":  f"${equity_now:,.2f}"
                    })
            equity_now += getattr(t,"net_pnl",0)
            if trade_time:
                rc.update_equity(equity_now, trade_time)
            trades_so_far.append(t)

        status = rc.get_status(equity_now)
        c1,c2,c3 = st.columns(3)
        c1.metric("Peak Equity",      f"${status['peak_equity']:,.2f}")
        c2.metric("Final Equity",     f"${status['current_equity']:,.2f}")
        c3.metric("Current Drawdown", fmt_p(status["drawdown_pct"]))
        st.divider()
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("**Limits Set**")
            st.markdown(f"- Max DD: `{max_dd_limit*100:.0f}%`")
            st.markdown(f"- Max Daily Loss: `{max_daily_loss*100:.0f}%`")
            st.markdown(f"- Max Consec Losses: `{max_consec_loss}`")
        with col2:
            dd_use = status["risk_usage_pct"]
            st.progress(min(dd_use/100, 1.0), text=f"DD usage: {dd_use:.1f}%")
            if dd_use > 80:   st.error("⚠️ Approaching DD limit!")
            elif dd_use > 50: st.warning("📊 DD at 50%+ of limit")
            else:             st.success("✅ Within safe limits")
        if halted_at:
            st.divider()
            st.warning(f"⚠️ Risk controller would have halted {len(halted_at)} time(s)")
            st.dataframe(pd.DataFrame(halted_at), width="stretch")
        else:
            st.success("✅ No risk limits triggered.")


# ═══════════════════════════════════════════════════════════════════
# TAB 11: All Results
# ═══════════════════════════════════════════════════════════════════
with tabs[10]:
    st.markdown("### 📦 Pre-Computed Results — All Instruments × Timeframes × Strategies")
    st.caption("Generated by `python run_all_tests.py`. Re-run it to refresh.")
    cache = load_results_cache()
    if not cache:
        st.info("No cached results found. Run `python run_all_tests.py` from your project root.")
    else:
        rows_all = []
        for key, r in cache.items():
            rows_all.append({
                "Symbol":        r.get("symbol",""),
                "Timeframe":     r.get("timeframe",""),
                "Strategy":      r.get("strategy",""),
                "Costs":         "✅" if r.get("costs_on") else "❌",
                "Trades":        r.get("total_trades",0),
                "Win Rate":      fmt_p(r.get("win_rate",0)*100),
                "Avg R":         round(r.get("average_r",0),3),
                "Net P&L":       fmt_d(r.get("net_pnl",0)),
                "Return":        fmt_p(r.get("return_pct",0)),
                "Max DD":        fmt_p(r.get("max_drawdown_pct",0)*100),
                "Profit Factor": f"{r.get('profit_factor',0):.2f}",
                "Status":        r.get("status","ok"),
            })
        df_all_res = pd.DataFrame(rows_all)
        col1,col2,col3 = st.columns(3)
        with col1:
            fsym   = st.multiselect("Symbol",  SYMBOLS, default=SYMBOLS, key="f_sym")
        with col2:
            fstrat = st.multiselect("Strategy", list(StrategyFactory.STRATEGIES.keys()),
                                    default=list(StrategyFactory.STRATEGIES.keys()), key="f_str")
        with col3:
            fsort  = st.selectbox("Sort by",["Net P&L","Return","Avg R","Win Rate","Trades"],key="f_sort")
        mask = df_all_res["Symbol"].isin(fsym) & df_all_res["Strategy"].isin(fstrat)
        df_filt = df_all_res[mask].copy()
        if fsort in ("Net P&L","Return"):
            df_filt = df_filt.sort_values(fsort,
                key=lambda col: col.apply(_parse_dollar), ascending=False)
        elif fsort == "Win Rate":
            df_filt = df_filt.sort_values(fsort,
                key=lambda col: col.apply(
                    lambda v: float(str(v).replace("%","")) if v else 0.0),
                ascending=False)
        elif fsort in ("Avg R","Trades"):
            df_filt = df_filt.sort_values(fsort, ascending=False)
        st.markdown(f"**{len(df_filt)} results**")
        st.dataframe(df_filt, width="stretch", height=520)
        st.download_button("⬇️ Download All Results CSV",
            df_filt.to_csv(index=False),
            "all_backtest_results.csv","text/csv")