import streamlit as st
import pandas as pd

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

# 🔽 ADD VIDEO HERE
st.video("https://youtu.be/l4KEN81CBvw")

st.divider()

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

        # 🔥 INDEX REMOVED HERE
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
