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
        # 🟢 EXPORT TO EXCEL (SINGLE SHEET - STOCK NAME)
        # =========================================================
        
        # 1. Create Summary DataFrame (Inputs + High-Level Results)
        summary_data = {
            "Parameter": [
                "Stock Name", "Spot Price", "Lot Size", "Option Lots",
                "Call SELL Strike", "Call SELL Price",
                "Call BUY Strike", "Call BUY Price",
                "Max Buy Steps", "Initial Leg %", "Coverage Ratio Required",
                "-----------------", "-----------------", # Separator
                "Calculated Breakeven", "Max Option Loss", "Total Shares Required",
                "Total Capital (Staggered)", "Average Buy Price", "Equity Profit @ BE"
            ],
            "Value": [
                stock_name, spot_price, lot_size, option_lots,
                call_sell_strike, call_sell_price,
                call_buy_strike, call_buy_price,
                steps, f"{initial_leg_percent}%", f"{coverage_ratio*100}%",
                "", "", # Separator
                round(breakeven, 2), option_loss, required_shares,
                staggered_capital, round(avg_price, 2), int(profit_at_be)
            ]
        }
        df_summary = pd.DataFrame(summary_data)

        # 2. Create Excel File with Single Sheet
        buffer = io.BytesIO()
        
        # Clean stock name for sheet usage (remove invalid chars just in case, or use as is)
        safe_sheet_name = "".join([c for c in stock_name if c.isalnum() or c in (' ','-','_')])[:30]
        if not safe_sheet_name: safe_sheet_name = "Plan"

        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            
            # Write Summary at the top
            df_summary.to_excel(writer, index=False, sheet_name=safe_sheet_name, startrow=0)
            
            # Get the workbook and sheet objects to write a header for the next section
            workbook = writer.book
            worksheet = writer.sheets[safe_sheet_name]
            
            # Define start row for the second table (Summary Rows + Header + Gap)
            start_row_plan = len(df_summary) + 4
            
            # Add a bold header for the Detailed Plan
            bold_fmt = workbook.add_format({'bold': True, 'font_size': 12})
            worksheet.write(start_row_plan - 1, 0, "Detailed Buying Plan", bold_fmt)
            
            # Write Detailed Plan below the summary
            df.to_excel(writer, index=False, sheet_name=safe_sheet_name, startrow=start_row_plan)
            
            # Auto-adjust column widths
            for i, col in enumerate(df_summary.columns):
                # Check width of both summary and detailed plan to set column width
                max_len_summary = max(df_summary[col].astype(str).map(len).max(), len(col))
                
                # Check corresponding column in detailed plan (if it exists)
                if i < len(df.columns):
                    max_len_plan = max(df.iloc[:, i].astype(str).map(len).max(), len(df.columns[i]))
                else:
                    max_len_plan = 0

                worksheet.set_column(i, i, max(max_len_summary, max_len_plan) + 2)

        buffer.seek(0)

        st.download_button(
            label=f"📥 Download {stock_name} Report (Excel)",
            data=buffer,
            file_name=f"{safe_sheet_name}_Staggered_Plan.xlsx",
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
