# from loader import load_price_data, detect_gaps
# from structure import detect_swings
# from strategy import BreakRetestStrategy

# data = load_price_data("data/BTC_M1.csv")
# gaps = detect_gaps(data, 1)
# swing_highs, swing_lows = detect_swings(data, gaps)

# strategy = BreakRetestStrategy(data, swing_highs, swing_lows)

# signals = 0

# for i in range(len(data)):
#     trade = strategy.on_candle(i)
#     if trade:
#         signals += 1
#         strategy.on_trade_closed()  # simulate immediate close for test

# print("Total signals detected:", signals)
