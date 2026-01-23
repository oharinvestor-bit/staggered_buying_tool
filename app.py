import streamlit as st
import pandas as pd
import io  # Required for file handling

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

# ============================
# BOOKING CTA WITH BUTTON
# ============================
st.markdown("""
<div style="
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #3b82f6;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
">
    <div style="flex: 1; min-width: 300px;">
        <p style="margin:0; color: #f8fafc; font-size: 15px; line-height: 1.5;">
            👋 <b>Need Personal Guidance?</b><br>
            If you have any doubts, want to discuss a strategy in detail, or need personal guidance, let's connect 1-on-1.
        </p>
    </div>
    <a href="https://superprofile.bio/bookings/beingsystemtrader" target="_blank" style="text-decoration: none;">
        <div style="
            background-color: #3b82f6;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: 0.3s;
        ">
            Book Session Here
        </div>
    </a>
</div>
""", unsafe_allow_html=True)

st.divider()

# NEW INPUT: Stock Name (Used for Sheet Name)
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
            base_capital,
            spot_price,
            call_sell_strike,
            steps,
            initial_leg_percent,
            breakeven,
            option_loss,
            required_shares,
            coverage_ratio
        )

        staggered_capital, profit_at_be, avg_price, total_qty, rows, covered_early = result

        # -------- METRICS --------
        st.subheader("📈 Option & Capital Metrics")

        c1, c2, c3 = st.columns(3)
        c1.metric("Required Shares", required_shares)
        c2.metric("Breakeven Price", round(breakeven, 2))
        c3.metric("Max Option Loss", f"₹{option_loss}")

        c4, c5 = st.columns(2)
        c4.metric("Capital (Lump Sum)", f"₹{base_capital}")
        c5.metric("Capital (Staggered)", f"₹{staggered_capital}")

        st.divider()

        # -------- STAGGERED BUY PLAN --------
        st.markdown("## 📋 **STAGGERED BUY PLAN**")

        df = pd.DataFrame(rows).reset_index(drop=True)

        styled_df = (
            df.style
            .format({
                "Buy Price": "₹{:,.2f}",
                "Capital Used (₹)": "₹{:,.0f}"
            })
            .applymap(lambda x: "color: green; font-weight: bold;", subset=["Buy Price"])
            .applymap(lambda x: "color: #003366; font-weight: bold;", subset=["Capital Used (₹)"])
            .set_properties(**{
                "font-size": "18px",
                "text-align": "center"
            })
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [
                        ("font-size", "19px"),
                        ("font-weight", "bold"),
                        ("text-align", "center")
                    ]
                }
            ])
        )

        st.dataframe(styled_df, use_container_width=True)

        # =========================================================
        # 🟢 EXPORT TO EXCEL (SINGLE ROW - WITH FLATTENED STEPS)
        # =========================================================
        
        # 1. Start with Summary Data
        flat_data = {
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
            "Coverage %": coverage_ratio * 100,
            "Breakeven": round(breakeven, 2),
            "Max Option Loss": option_loss,
            "Total Shares": required_shares,
            "Total Capital": staggered_capital,
            "Avg Buy Price": round(avg_price, 2),
            "Equity Profit @ BE": int(profit_at_be),
            "Status": "Covered Early" if covered_early else "Full Steps"
        }

        # 2. Append Detailed Buying Steps Horizontally
        # Loop through the calculation 'rows' and add them as columns
        for idx, row_data in enumerate(rows):
            step_num = idx + 1
            flat_data[f"STEP-{step_num}"] = row_data["Step"]
            flat_data[f"BUY PRICE-{step_num}"] = row_data["Buy Price"]
            flat_data[f"QUANTITY-{step_num}"] = row_data["Quantity"]
            flat_data[f"CAPITAL USED-{step_num}"] = row_data["Capital Used (₹)"]

        # 3. Create DataFrame
        df_export = pd.DataFrame([flat_data])

        buffer = io.BytesIO()
        
        safe_filename_prefix = "".join([c for c in stock_name if c.isalnum() or c in (' ','-','_')])[:30]
        if not safe_filename_prefix: safe_filename_prefix = "TradePlan"

        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Trade Log')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Trade Log']
            for i, col in enumerate(df_export.columns):
                # Check length of data and header
                max_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)

        buffer.seek(0)

        st.download_button(
            label=f"📥 Download {stock_name} Full Log (Row Format)",
            data=buffer,
            file_name=f"{safe_filename_prefix}_Full_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        # =========================================================

        st.divider()

        # -------- FINAL VALIDATION --------
        st.subheader("✅ Final Validation")

        f1, f2, f3 = st.columns(3)
        f1.metric("Avg Buy Price", f"₹{round(avg_price,2)}")
        f2.metric("Total Shares", total_qty)
        f3.metric("Equity MTM @ BE", f"₹{int(profit_at_be)}")

        if covered_early:
            st.success("Position became COVERED before final step ✔️")
        elif profit_at_be >= coverage_ratio * option_loss:
            st.success("MTM Positive at Breakeven ✔️")
        else:
            st.warning("Hedge insufficient ❗")
