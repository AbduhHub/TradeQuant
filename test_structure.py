# from loader import load_price_data, detect_gaps
# from structure import detect_swings

# data = load_price_data("data/BTC_M1.csv")
# gaps = detect_gaps(data, timeframe_minutes=1)

# swing_highs, swing_lows = detect_swings(data, gaps)

# print("Swing highs:", len(swing_highs))
# print("Swing lows:", len(swing_lows))

# # Sanity check first few
# print("First swing high index:", min(swing_highs))
# print("First swing low index:", min(swing_lows))
