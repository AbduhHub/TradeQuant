"""
Metrics Module - Extended
Computes R-based and dollar-based performance metrics.
"""
from typing import List, Dict


def calculate_metrics(trades, initial_capital: float = 10000.0) -> Dict:
    if not trades:
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'breakevens': 0,
            'win_rate': 0.0,
            'average_r': 0.0,
            'total_r': 0.0,
            'max_drawdown_r': 0.0,
            'profit_factor': 0.0,
            'net_pnl': 0.0,
            'gross_pnl': 0.0,
            'total_costs': 0.0,
            'max_drawdown_pct': 0.0,
            'sharpe': 0.0,
            'avg_win_r': 0.0,
            'avg_loss_r': 0.0,
            'final_capital': initial_capital,
            'return_pct': 0.0,
        }

    total_r = peak = drawdown = max_dd = 0.0
    wins = losses = breakevens = 0
    gross_wins = gross_losses = 0.0
    net_pnl = gross_pnl = total_costs = 0.0
    win_rs = []
    loss_rs = []

    equity = initial_capital
    eq_peak = equity
    max_dd_pct = 0.0

    for t in trades:
        r = getattr(t, 'total_r', 0.0)
        total_r += r

        if r > 0:
            wins += 1
            win_rs.append(r)
        elif r < 0:
            losses += 1
            loss_rs.append(r)
        else:
            breakevens += 1

        peak = max(peak, total_r)
        drawdown = peak - total_r
        max_dd = max(max_dd, drawdown)

        # Dollar P&L
        net = getattr(t, 'net_pnl', 0.0)
        gross = getattr(t, 'gross_pnl', 0.0)
        costs = getattr(t, 'total_costs', 0.0)
        net_pnl += net
        gross_pnl += gross
        total_costs += costs

        if gross > 0:
            gross_wins += gross
        else:
            gross_losses += abs(gross)

        # Equity-based drawdown
        equity += net
        eq_peak = max(eq_peak, equity)
        dd_pct = (eq_peak - equity) / eq_peak if eq_peak > 0 else 0
        max_dd_pct = max(max_dd_pct, dd_pct)

    n = len(trades)
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float('inf')

    # Sharpe: mean_r / std_r (trade-level, unannualized — sufficient for comparison)
    all_rs = win_rs + loss_rs
    if len(all_rs) > 1:
        mean_r = sum(all_rs) / len(all_rs)
        var_r  = sum((r - mean_r) ** 2 for r in all_rs) / len(all_rs)
        std_r  = var_r ** 0.5
        sharpe = (mean_r / std_r) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        'total_trades': n,
        'wins': wins,
        'losses': losses,
        'breakevens': breakevens,
        'win_rate': wins / n,
        'average_r': total_r / n,
        'total_r': total_r,
        'max_drawdown_r': max_dd,
        'profit_factor': profit_factor,
        'net_pnl': net_pnl,
        'gross_pnl': gross_pnl,
        'total_costs': total_costs,
        'max_drawdown_pct': max_dd_pct,
        'sharpe': sharpe,
        'avg_win_r': sum(win_rs) / len(win_rs) if win_rs else 0.0,
        'avg_loss_r': sum(loss_rs) / len(loss_rs) if loss_rs else 0.0,
        'final_capital': initial_capital + net_pnl,
        'return_pct': (net_pnl / initial_capital) * 100 if initial_capital else 0.0,
    }