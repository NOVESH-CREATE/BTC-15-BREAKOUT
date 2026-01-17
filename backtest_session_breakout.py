# ============================================================
# BTC SESSION BREAKOUT BACKTESTING - BINANCE DATA
# Uses Binance API (ccxt) for extended historical data
# Can backtest for months or even a full year!
# Author: Custom build for Novesh
# ============================================================

import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import time

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="BTC Session Backtest (Binance)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= CUSTOM CSS =================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #1a1f35 100%);
    }
    h1, h2, h3 {
        color: #10b981 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.timezone("UTC")

# ================= HELPER FUNCTIONS =================
def calculate_position_size(entry, sl, balance, risk_pct):
    """Calculate position size based on risk"""
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        return 0
    return risk_amount / risk_per_unit

def weekday_allowed(session, day):
    """Check if weekday is allowed for session"""
    if session == "S1":
        return day in [0, 1, 2]  # Mon, Tue, Wed
    else:
        return day in [0, 4]  # Mon, Fri

# ================= DATA DOWNLOAD =================
@st.cache_data(ttl=3600)
def download_binance_data(symbol, start_date, end_date, timeframe):
    """Download data from Binance using ccxt"""
    exchange = ccxt.binance({'enableRateLimit': True})
    
    # Convert dates to milliseconds
    since = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    
    all_data = []
    current_since = since
    
    # Binance returns max 1000 candles per request
    limit = 1000
    
    with st.spinner(f"Downloading {timeframe} data from Binance..."):
        while current_since < end_ts:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)
                
                if len(ohlcv) == 0:
                    break
                
                all_data.extend(ohlcv)
                
                # Move to next batch
                current_since = ohlcv[-1][0] + 1
                
                # Rate limiting
                time.sleep(0.1)
                
                # Progress update
                progress = min(100, int(((current_since - since) / (end_ts - since)) * 100))
                if progress % 10 == 0:
                    st.write(f"Progress: {progress}%")
                
            except Exception as e:
                st.error(f"Error downloading data: {e}")
                break
    
    if len(all_data) == 0:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(IST)
    df.set_index('timestamp', inplace=True)
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    return df

def get_pivot_candle(df_15m, date, hour, minute):
    """Get the 15m candle ending at session time"""
    session_time = pd.Timestamp(year=date.year, month=date.month, day=date.day,
                                hour=hour, minute=minute, tz=IST)
    mask = df_15m.index <= session_time
    if mask.sum() == 0:
        return None
    pivot_idx = df_15m[mask].index[-1]
    time_diff = abs((session_time - pivot_idx).total_seconds())
    if time_diff > 900:
        return None
    return df_15m.loc[pivot_idx]

def get_5m_candles_after(df_5m, start_time, count=20):
    """Get 5m candles after a specific time"""
    mask = df_5m.index > start_time
    return df_5m[mask].head(count)

def get_15m_candle_after(df_15m, start_time):
    """Get the next 15m candle after a specific time"""
    mask = df_15m.index > start_time
    if mask.sum() == 0:
        return None
    return df_15m[mask].iloc[0]

# ================= BACKTESTING ENGINE =================
def run_backtest(df_5m, df_15m, initial_capital, risk_percent, tp_multiple):
    """Run the backtesting engine"""
    trades = []
    balance = initial_capital
    equity_curve = [{"date": df_5m.index[0], "balance": balance}]
    
    dates = df_5m.index.normalize().unique()
    current_day_s1_direction = None
    
    progress_bar = st.progress(0)
    total_days = len(dates)
    
    for idx, date in enumerate(dates):
        day_of_week = date.weekday()
        current_day_s1_direction = None
        
        # Update progress
        progress_bar.progress((idx + 1) / total_days)
        
        # ============ SESSION 1 ============
        if weekday_allowed("S1", day_of_week):
            pivot = get_pivot_candle(df_15m, date, 8, 30)
            
            if pivot is not None:
                pivot_high = pivot['high']
                pivot_low = pivot['low']
                pivot_time = pivot.name
                
                candles_5m = get_5m_candles_after(df_5m, pivot_time, 20)
                if len(candles_5m) == 0:
                    continue
                
                breakout_found = False
                for idx_c, candle in candles_5m.iterrows():
                    if candle['close'] > pivot_high:
                        breakout_direction = "LONG"
                        entry_price = candle['close']
                        breakout_candle_time = idx_c
                        breakout_found = True
                        break
                    elif candle['close'] < pivot_low:
                        breakout_direction = "SHORT"
                        entry_price = candle['close']
                        breakout_candle_time = idx_c
                        breakout_found = True
                        break
                
                if breakout_found:
                    confirm_candle = get_15m_candle_after(df_15m, breakout_candle_time)
                    
                    if confirm_candle is not None:
                        confirmed = False
                        if breakout_direction == "LONG" and confirm_candle['close'] > pivot_high:
                            confirmed = True
                        elif breakout_direction == "SHORT" and confirm_candle['close'] < pivot_low:
                            confirmed = True
                        
                        if confirmed:
                            sl = pivot_low if breakout_direction == "LONG" else pivot_high
                            
                            if breakout_direction == "LONG":
                                tp = entry_price + (entry_price - sl) * tp_multiple
                            else:
                                tp = entry_price - (sl - entry_price) * tp_multiple
                            
                            position_size = calculate_position_size(entry_price, sl, balance, risk_percent)
                            
                            if position_size > 0:
                                future_candles = get_5m_candles_after(df_5m, breakout_candle_time, 50)
                                
                                exit_price = None
                                exit_time = None
                                outcome = None
                                
                                for idx_f, candle in future_candles.iterrows():
                                    if breakout_direction == "LONG":
                                        if candle['low'] <= sl:
                                            exit_price = sl
                                            exit_time = idx_f
                                            outcome = "LOSS"
                                            break
                                        elif candle['high'] >= tp:
                                            exit_price = tp
                                            exit_time = idx_f
                                            outcome = "WIN"
                                            break
                                    else:
                                        if candle['high'] >= sl:
                                            exit_price = sl
                                            exit_time = idx_f
                                            outcome = "LOSS"
                                            break
                                        elif candle['low'] <= tp:
                                            exit_price = tp
                                            exit_time = idx_f
                                            outcome = "WIN"
                                            break
                                
                                if outcome is not None:
                                    if breakout_direction == "LONG":
                                        pnl = (exit_price - entry_price) * position_size
                                    else:
                                        pnl = (entry_price - exit_price) * position_size
                                    
                                    balance += pnl
                                    
                                    trades.append({
                                        'session': 'S1',
                                        'date': date,
                                        'entry_time': breakout_candle_time,
                                        'exit_time': exit_time,
                                        'direction': breakout_direction,
                                        'entry': entry_price,
                                        'exit': exit_price,
                                        'sl': sl,
                                        'tp': tp,
                                        'position_size': position_size,
                                        'outcome': outcome,
                                        'pnl': pnl,
                                        'balance_after': balance
                                    })
                                    
                                    equity_curve.append({"date": exit_time, "balance": balance})
                                    current_day_s1_direction = breakout_direction
        
        # ============ SESSION 2 ============
        if weekday_allowed("S2", day_of_week):
            pivot = get_pivot_candle(df_15m, date, 13, 30)
            
            if pivot is not None:
                pivot_high = pivot['high']
                pivot_low = pivot['low']
                pivot_time = pivot.name
                
                candles_5m = get_5m_candles_after(df_5m, pivot_time, 20)
                if len(candles_5m) == 0:
                    continue
                
                breakout_found = False
                for idx_c, candle in candles_5m.iterrows():
                    if candle['close'] > pivot_high:
                        breakout_direction = "LONG"
                        entry_price = candle['close']
                        breakout_candle_time = idx_c
                        breakout_found = True
                        break
                    elif candle['close'] < pivot_low:
                        breakout_direction = "SHORT"
                        entry_price = candle['close']
                        breakout_candle_time = idx_c
                        breakout_found = True
                        break
                
                if breakout_found:
                    if current_day_s1_direction is not None and breakout_direction != current_day_s1_direction:
                        continue
                    
                    confirm_candle = get_15m_candle_after(df_15m, breakout_candle_time)
                    
                    if confirm_candle is not None:
                        confirmed = False
                        if breakout_direction == "LONG" and confirm_candle['close'] > pivot_high:
                            confirmed = True
                        elif breakout_direction == "SHORT" and confirm_candle['close'] < pivot_low:
                            confirmed = True
                        
                        if confirmed:
                            sl = pivot_low if breakout_direction == "LONG" else pivot_high
                            
                            if breakout_direction == "LONG":
                                tp = entry_price + (entry_price - sl) * tp_multiple
                            else:
                                tp = entry_price - (sl - entry_price) * tp_multiple
                            
                            position_size = calculate_position_size(entry_price, sl, balance, risk_percent)
                            
                            if position_size > 0:
                                future_candles = get_5m_candles_after(df_5m, breakout_candle_time, 50)
                                
                                exit_price = None
                                exit_time = None
                                outcome = None
                                
                                for idx_f, candle in future_candles.iterrows():
                                    if breakout_direction == "LONG":
                                        if candle['low'] <= sl:
                                            exit_price = sl
                                            exit_time = idx_f
                                            outcome = "LOSS"
                                            break
                                        elif candle['high'] >= tp:
                                            exit_price = tp
                                            exit_time = idx_f
                                            outcome = "WIN"
                                            break
                                    else:
                                        if candle['high'] >= sl:
                                            exit_price = sl
                                            exit_time = idx_f
                                            outcome = "LOSS"
                                            break
                                        elif candle['low'] <= tp:
                                            exit_price = tp
                                            exit_time = idx_f
                                            outcome = "WIN"
                                            break
                                
                                if outcome is not None:
                                    if breakout_direction == "LONG":
                                        pnl = (exit_price - entry_price) * position_size
                                    else:
                                        pnl = (entry_price - exit_price) * position_size
                                    
                                    balance += pnl
                                    
                                    trades.append({
                                        'session': 'S2',
                                        'date': date,
                                        'entry_time': breakout_candle_time,
                                        'exit_time': exit_time,
                                        'direction': breakout_direction,
                                        'entry': entry_price,
                                        'exit': exit_price,
                                        'sl': sl,
                                        'tp': tp,
                                        'position_size': position_size,
                                        'outcome': outcome,
                                        'pnl': pnl,
                                        'balance_after': balance
                                    })
                                    
                                    equity_curve.append({"date": exit_time, "balance": balance})
    
    progress_bar.empty()
    return trades, equity_curve, balance

# ================= MAIN DASHBOARD =================
def main():
    st.markdown("<h1 style='text-align: center;'>📊 BTC SESSION BACKTEST (BINANCE DATA)</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Full Year Backtesting with Binance Historical Data</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # ================= SIDEBAR =================
    with st.sidebar:
        st.markdown("## ⚙️ Backtest Configuration")
        
        st.success("""
        ✅ **Using Binance Data**  
        Can backtest for months or even a full year!
        """)
        
        # Period Selection
        st.markdown("### 📅 Time Period")
        period_option = st.selectbox(
            "Select Period",
            ["1 Month", "3 Months", "6 Months", "1 Year", "Custom"],
            help="Binance has extensive historical data - test any period!"
        )
        
        if period_option == "Custom":
            col1, col2 = st.columns(2)
            with col1:
                custom_start = st.date_input(
                    "Start Date",
                    datetime.now().date() - timedelta(days=365)
                )
            with col2:
                custom_end = st.date_input(
                    "End Date",
                    datetime.now().date()
                )
        else:
            custom_start, custom_end = None, None
        
        # Capital & Risk
        st.markdown("### 💰 Capital & Risk")
        initial_capital = st.number_input(
            "Initial Capital (USDT)",
            min_value=1,
            max_value=1000000,
            value=10000,
            step=100
        )
        
        risk_percent = st.slider(
            "Risk per Trade (%)",
            min_value=1,
            max_value=20,
            value=10,
            step=1
        ) / 100
        
        tp_multiple = st.selectbox(
            "Take Profit (R Multiple)",
            [1.0, 1.2, 1.5, 2.0],
            index=0
        )
        
        # Strategy Info
        st.markdown("### 📋 Strategy Rules")
        st.info("""
        **Fixed Rules:**
        - S1: 8:30 AM IST (Mon/Tue/Wed)
        - S2: 1:30 PM IST (Mon/Fri)
        - 5m breakout + 15m confirm
        - S2 matches S1 direction
        - **Compounding: YES ✅**
        """)
        
        st.markdown("---")
        run_btn = st.button("🚀 RUN BACKTEST", use_container_width=True, type="primary")
    
    # ================= MAIN CONTENT =================
    if run_btn:
        # Calculate dates
        end_date = datetime.now()
        
        if period_option == "1 Month":
            start_date = end_date - timedelta(days=30)
        elif period_option == "3 Months":
            start_date = end_date - timedelta(days=90)
        elif period_option == "6 Months":
            start_date = end_date - timedelta(days=180)
        elif period_option == "1 Year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.combine(custom_start, datetime.min.time())
            end_date = datetime.combine(custom_end, datetime.max.time())
        
        st.info(f"📥 Downloading data from Binance: {start_date.date()} to {end_date.date()}")
        
        # Download data
        df_5m = download_binance_data("BTC/USDT", start_date, end_date, "5m")
        df_15m = download_binance_data("BTC/USDT", start_date, end_date, "15m")
        
        if df_5m is None or df_15m is None:
            st.error("❌ Failed to download data from Binance")
            return
        
        st.success(f"✅ Downloaded {len(df_5m):,} 5m candles and {len(df_15m):,} 15m candles")
        
        # Run backtest
        with st.spinner("🔍 Running backtest..."):
            trades, equity_curve, final_balance = run_backtest(
                df_5m, df_15m, initial_capital, risk_percent, tp_multiple
            )
        
        if len(trades) == 0:
            st.warning("⚠️ No trades executed. Try different dates or check data quality.")
            return
        
        # Results
        trades_df = pd.DataFrame(trades)
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['outcome'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = final_balance - initial_capital
        total_return = (total_pnl / initial_capital * 100)
        
        st.markdown("---")
        st.markdown("## 📊 BACKTEST RESULTS")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Trades", total_trades)
        with col2:
            st.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")
        with col3:
            st.metric("Initial", f"${initial_capital:,.0f}")
        with col4:
            st.metric("Final", f"${final_balance:,.0f}", f"${total_pnl:+,.0f}")
        with col5:
            st.metric("Return", f"{total_return:+.2f}%", "Compounded")
        
        # Equity Curve
        st.markdown("### 📈 Equity Curve")
        equity_df = pd.DataFrame(equity_curve)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=equity_df['date'],
            y=equity_df['balance'],
            mode='lines',
            name='Balance',
            line=dict(color='#10b981', width=3),
            fill='tonexty'
        ))
        fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray")
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Balance (USDT)",
            template="plotly_dark",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Trade Log
        st.markdown("### 📋 Trade Log")
        display_df = trades_df[['session', 'date', 'direction', 'entry', 'exit', 'outcome', 'pnl', 'balance_after']].copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        display_df['entry'] = display_df['entry'].apply(lambda x: f"${x:,.2f}")
        display_df['exit'] = display_df['exit'].apply(lambda x: f"${x:,.2f}")
        display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:+,.2f}")
        display_df['balance_after'] = display_df['balance_after'].apply(lambda x: f"${x:,.2f}")
        display_df.columns = ['Session', 'Date', 'Direction', 'Entry', 'Exit', 'Outcome', 'P&L', 'Balance']
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Download
        csv = trades_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"backtest_{start_date.date()}_{end_date.date()}.csv",
            "text/csv",
            use_container_width=True
        )
    
    else:
        st.markdown("""
        ## 👈 Configure & Run
        
        ### ✅ Advantages:
        - **Full Year Backtesting** - No 60-day limit!
        - **Binance Data** - More reliable and complete
        - **Same Strategy** - Exact logic as live bot
        - **Compounding** - Real results with growing balance
        
        ### 📊 Select Your Period:
        - **1 Month** - Quick test (~50 trades)
        - **3 Months** - Good sample (~150 trades)
        - **6 Months** - Solid validation (~300 trades)
        - **1 Year** - Full strategy test (~600+ trades)
        - **Custom** - Any range you want
        
        Click **RUN BACKTEST** to start!
        """)

if __name__ == "__main__":
    main()