import streamlit as st
import pandas as pd
import io

# ---------------- CORE LOGIC ---------------- #

def required_staggered_capital(
    base_capital,
    spot_price,
    final_buy_price,
    steps,
    initial_leg_percent,
    breakeven,
    option_loss,
    required_shares,
    coverage_ratio=0.70,
    max_iter=300
):
    capital = int(round(base_capital))

    for _ in range(max_iter):
        first_leg = int(round(capital * (initial_leg_percent / 100)))
        remaining = capital - first_leg
        step_gap = (final_buy_price - spot_price) / (steps - 1)

        total_qty = 0
        total_cost = 0
        rows = []

        for i in range(steps):
            price = spot_price + i * step_gap
            cap = first_leg if i == 0 else remaining // (steps - 1)
            qty = int(round(cap / price))
            actual_capital = qty * price

            total_qty += qty
            total_cost += actual_capital

            rows.append({
                "Step": i + 1,
                "Buy Price": round(price, 2),
                "Quantity": qty,
                "Capital Used (₹)": actual_capital
            })

            # 🟢 COVERED CALL EARLY STOP
            if total_qty >= required_shares:
                avg_price = total_cost / total_qty
                equity_profit = (breakeven - avg_price) * total_qty
                return capital, equity_profit, avg_price, total_qty, rows, True

        avg_price = total_cost / total_qty
        equity_profit = (breakeven - avg_price) * total_qty

        if equity_profit >= coverage_ratio * option_loss:
            return capital, equity_profit, avg_price, total_qty, rows, False

        capital = int(capital * 1.02)

    return capital, equity_profit, avg_price, total_qty, rows, False


# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(page_title="Staggered Buying Tool", layout="centered")

st.title("📊 Staggered Buying Calculator")
st.caption("Calculates Amount of Equity to be Purchased in a Covered Call Spread. Created by Nitin Joshi | Being System Trader")

# Booking CTA
st.markdown("""
<div style="background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #3b82f6; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
    <div style="flex: 1; min-width: 300px;">
        <p style="margin:0; color: #f8fafc; font-size: 15px; line-height: 1.5;">
            👋 <b>Need Personal Guidance?</b><br>
            If you have any doubts, want to discuss a strategy in detail, or need personal guidance, let's connect 1-on-1.
        </p>
    </div>
    <a href="https://superprofile.bio/bookings/beingsystemtrader" target="_blank" style="text-decoration: none;">
        <div style="background-color: #3b82f6; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 14px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: 0.3s;">
            Book Session Here
        </div>
    </a>
</div>
""", unsafe_allow_html=True)

st.divider()

# Inputs
stock_name = st.text_input("Stock Name / Symbol", value="STOCK")
spot_price = st.number_input("Current Spot Price", value=1500.0)
lot_size = st.number_input("Lot Size (per option)", value=500)
option_lots = st.number_input("Number of Option Lots Executed", min_value=1, value=1)

st.subheader("📌 Call Details")
call_sell_strike = st.number_input("Call SELL Strike", value=1530.0)
call_sell_price = st.number_input("Call SELL Premium", value=15.0)
call_buy_strike = st.number_input("Call BUY Strike", value=1540.0)
call_buy_price = st.number_input("Call BUY Premium", value=10.0)

st.subheader("📌 Execution Plan")
steps = st.slider("Maximum Buy Steps", min_value=2, max_value=10, value=5)
initial_leg_percent = st.slider("Initial Leg %", 0, 100
