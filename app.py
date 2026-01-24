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
call_sell_price = st.number_input("Call SELL Price", value=15.0)
call_buy_strike = st.number_input("Call BUY Strike", value=1540.0)
call_buy_price = st.number_input("Call BUY Price", value=10.0)

st.subheader("📌 Execution Plan")
steps = st.slider("Maximum Buy Steps", min_value=2, max_value=10, value=5)
initial_leg_percent = st.slider("Initial Leg %", 0, 100, 40)
coverage_ratio = st.slider("MTM Coverage Required (%)", 50, 100, 70) / 100

st.divider()

if st.button("🚀 Calculate"):
    required_shares = lot_size * option_lots
    net_credit = call_sell_price - call_buy_price
    spread_width = abs(call_sell_strike - call_buy_strike)
    max_loss_per_share = max(spread_width - net_credit, 0)
    option_loss = int(max_loss_per_share * required_shares)
    breakeven = call_sell_strike + net_credit
    distance_percent = (breakeven - spot_price) / spot_price

    if distance_percent <= 0:
        st.error("Breakeven must be above spot price")
    else:
        base_capital = int(option_loss / distance_percent) if option_loss > 0 else 0
        result = required_staggered_capital(
            base_capital, spot_price, call_sell_strike, steps,
            initial_leg_percent, breakeven, option_loss, required_shares, coverage_ratio
        )

        staggered_capital, profit_at_be, avg_price, total_qty, rows, covered_early = result

        # Display Metrics
        st.subheader("📈 Option & Capital Metrics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Required Shares", required_shares)
        c2.metric("Breakeven Price", round(breakeven, 2))
        c3.metric("Max Option Loss", f"₹{option_loss}")

        st.divider()

        # 🟢 UPDATED VERTICAL EXPORT LOGIC (Matching Image Headers)
        export_dict = {
            "Stock Name": stock_name,
            "Spot Price": spot_price,
            "Lot Size": lot_size,
            "Option Lots": option_lots,
            "Call SELL Strike": call_sell_strike,
            "Call SELL Price": call_sell_price,
            "Call BUY Strike": call_buy_strike,
            "Call BUY Price": call_buy_price,
            "Steps": steps,
            "Initial Leg %": initial_leg_percent,
            "Coverage %": f"{coverage_ratio * 100}%",
            "Breakeven": round(breakeven, 2),
            "--- RESULTS ---": "---",
            "Total Shares Required": required_shares,
            "Total Capital Needed": staggered_capital,
            "Avg Buy Price": round(avg_price, 2),
            "Equity Profit @ BE": int(profit_at_be),
            "Status": "Covered Early" if covered_early else "Full Steps Completed"
        }

        # Add Steps vertically
        for idx, r in enumerate(rows):
            s = idx + 1
            export_dict[f"Step {s} Price"] = r["Buy Price"]
            export_dict[f"Step {s} Qty"] = r["Quantity"]
            export_dict[f"Step {s} Capital"] = r["Capital Used (₹)"]

        # Transpose into two columns
        df_export = pd.Series(export_dict).reset_index()
        df_export.columns = ["Header", "Data"]

        # Excel File Generation
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='TradePlan')
            workbook  = writer.book
            worksheet = writer.sheets['TradePlan']
            
            # Formats
            bold_fmt = workbook.add_format({'bold': True, 'bg_color': '#EFEFEF', 'border': 1})
            val_fmt = workbook.add_format({'border': 1})
            
            worksheet.set_column(0, 0, 30, bold_fmt)
            worksheet.set_column(1, 1, 25, val_fmt)

        buffer.seek(0)
        
        st.download_button(
            label=f"📥 Download {stock_name} Export",
            data=buffer,
            file_name=f"{stock_name}_Plan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("Calculation Complete! You can now download the vertical export.")
