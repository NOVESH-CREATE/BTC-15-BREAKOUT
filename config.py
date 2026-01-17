# ============================================================
# BACKTEST CONFIGURATION FILE
# Edit this file to test different parameters
# ============================================================

# DATA SETTINGS
SYMBOL = "BTC-USD"              # Yahoo Finance symbol (BTC-USD, ETH-USD, etc.)
START_DATE = "2024-01-01"       # Backtest start date (YYYY-MM-DD)
END_DATE = "2025-01-17"         # Backtest end date (YYYY-MM-DD)

# CAPITAL & RISK
INITIAL_CAPITAL = 10000         # Starting balance in USD
RISK_PERCENT = 0.10             # Risk per trade (0.10 = 10%)
TP_R_MULTIPLE = 1.0             # Take profit multiple (1.0 = 1R, 1.5 = 1.5R)

# SESSION TIMES (IST TIMEZONE)
S1_HOUR = 8                     # S1 (London) hour (0-23)
S1_MINUTE = 30                  # S1 (London) minute (0-59)
S2_HOUR = 13                    # S2 (NY) hour (0-23)
S2_MINUTE = 30                  # S2 (NY) minute (0-59)

# WEEKDAY FILTERS
# Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
S1_ALLOWED_DAYS = [0, 1, 2]     # S1 allowed weekdays [Mon, Tue, Wed]
S2_ALLOWED_DAYS = [0, 4]        # S2 allowed weekdays [Mon, Fri]

# ============================================================
# TESTING SCENARIOS - UNCOMMENT TO TRY
# ============================================================

# --- AGGRESSIVE TRADING ---
# RISK_PERCENT = 0.15           # 15% risk
# TP_R_MULTIPLE = 1.5           # 1.5R target

# --- CONSERVATIVE TRADING ---
# RISK_PERCENT = 0.05           # 5% risk
# TP_R_MULTIPLE = 1.0           # 1R target

# --- TEST ALL WEEKDAYS ---
# S1_ALLOWED_DAYS = [0, 1, 2, 3, 4]  # All weekdays
# S2_ALLOWED_DAYS = [0, 1, 2, 3, 4]  # All weekdays

# --- S1 ONLY (NO S2) ---
# S2_ALLOWED_DAYS = []          # Disable S2 completely

# --- S2 ONLY (NO S1) ---
# S1_ALLOWED_DAYS = []          # Disable S1 completely

# --- DIFFERENT SESSION TIMES ---
# S1_HOUR = 9                   # 9:30 AM instead of 8:30 AM
# S2_HOUR = 14                  # 2:30 PM instead of 1:30 PM

# --- 2R TARGET ---
# TP_R_MULTIPLE = 2.0           # 2R target (larger profit, lower win rate)

# --- ETHEREUM ---
# SYMBOL = "ETH-USD"            # Test on Ethereum instead

# --- LONGER BACKTEST ---
# START_DATE = "2023-01-01"     # 2-year backtest

# --- RECENT DATA ONLY ---
# START_DATE = "2024-06-01"     # Last 6 months only

# ============================================================
# NOTES
# ============================================================
# 
# After editing this file, run:
#   python backtest_session_breakout.py
# 
# The script will automatically load these settings.
# 
# TIP: Make a copy of this file before testing:
#   cp config.py config_backup.py
# 
# ============================================================
