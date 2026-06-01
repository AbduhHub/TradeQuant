"""
Backtester — v5
- Instrument-aware position sizing using UNIFIED raw-price system
- All sizes in base-currency units (BTC, oz, EUR) with pip_value=1.0
- No equity_curve list (memory waste on 1.6M candle runs)
- Gap-aware forced close

SIZING CONVENTION (matches trade.py gross_pnl = price_diff * size):
  risk_amount = sl_distance * size
  size = risk_amount / sl_distance          (pip_value=1.0 for all)
  gross_pnl = price_diff * size             (correct for USD-quoted instruments)

Unit interpretation per instrument:
  BTCUSD : size = BTC coins           (price in USD/BTC → diff*size = USD)
  XAUUSD : size = troy oz             (price in USD/oz  → diff*size = USD)
  EURUSD : size = EUR units           (price in USD/EUR → diff*size = USD)

Cost model must also express costs per BASE UNIT (see transaction_costs.py).
"""
from trade import Trade
from costs.transaction_costs import InstrumentConfig


# All pip_value=1.0: raw price diff × base-unit size = USD P&L.
# max/min are in base units to keep 1% risk sensible on $10k capital.
_INST_PARAMS = {
    'BTCUSD': {'pip_value': 1.0, 'max_lots': 2.5,      'min_lots': 0.001},
    # XAUUSD: max=50 oz (0.5 standard lots), costs per oz
    # 50 oz × ~$2500/oz = $125k notional = 12.5:1 max leverage on $10k account
    # Prevents overleverage on small-ATR timeframes (M1/M5/M15)
    'XAUUSD': {'pip_value': 1.0, 'max_lots': 50.0,     'min_lots': 0.01},
    # EURUSD: max=900_000 EUR (9 standard lots), costs per EUR unit
    'EURUSD': {'pip_value': 1.0, 'max_lots': 900000.0, 'min_lots': 1000.0},
    'GBPUSD': {'pip_value': 1.0, 'max_lots': 900000.0, 'min_lots': 1000.0},
}
_DEFAULT_PARAMS = {'pip_value': 1.0, 'max_lots': 10.0, 'min_lots': 0.01}


class Backtester:
    def __init__(self, candles, gaps, strategy,
                 cost_model=None, capital=10000.0, risk_pct=0.01,
                 instrument='BTCUSD'):
        self.candles    = candles
        self.gaps       = gaps
        self.strategy   = strategy
        self.cost_model = cost_model
        self.capital    = capital
        self.initial_capital = capital
        self.risk_pct   = risk_pct
        self.instrument = instrument
        self.inst_p     = _INST_PARAMS.get(instrument, _DEFAULT_PARAMS)
        self.open_trade = None
        self.trades     = []

    def _position_size(self, entry_price: float, sl: float) -> float:
        """
        Unified raw-price sizing:
            size = risk_amount / sl_distance
        Works for all USD-quoted instruments (BTC, XAU, EUR) because
            gross_pnl = price_diff * size  is already in USD.
        """
        if sl is None or sl == 0 or entry_price == 0:
            return self.inst_p['min_lots']

        sl_distance = abs(entry_price - sl)
        if sl_distance == 0:
            return self.inst_p['min_lots']

        risk_amount = self.capital * self.risk_pct
        size = risk_amount / sl_distance   # pip_value == 1.0 for all

        return max(self.inst_p['min_lots'],
                   min(size, self.inst_p['max_lots']))

    def run(self):
        equity = self.capital

        for i, candle in enumerate(self.candles):
            is_gap = i in self.gaps

            # Force-close on gap
            if is_gap and self.open_trade:
                gap_price = self.candles[i]['open']
                if not self.open_trade.is_closed:
                    self.open_trade._close(i, gap_price)
                equity += self.open_trade.net_pnl
                self.capital = max(equity, 0.0)
                self.trades.append(self.open_trade)
                self.open_trade = None

            # Check exit
            if self.open_trade:
                if self.open_trade.check_exit(i, candle):
                    equity += self.open_trade.net_pnl
                    self.capital = max(equity, 0.0)
                    self.trades.append(self.open_trade)
                    self.open_trade = None

            # Entry
            if self.open_trade is None and not is_gap:
                raw = self.strategy.on_candle(i)
                if raw:
                    size = self._position_size(raw.entry_price, raw.sl)
                    self.open_trade = Trade(
                        entry_idx=raw.entry_idx,
                        entry_price=raw.entry_price,
                        direction=raw.direction,
                        sl=raw.sl,
                        tp=raw.tp,
                        size=size,
                        cost_model=self.cost_model
                    )

        # Force-close final open trade
        if self.open_trade:
            last_idx = len(self.candles) - 1
            close_price = self.candles[last_idx]['close']
            if not self.open_trade.is_closed:
                self.open_trade._close(last_idx, close_price)
            equity += self.open_trade.net_pnl
            self.capital = max(equity, 0.0)
            self.trades.append(self.open_trade)
            self.open_trade = None

        return self.trades