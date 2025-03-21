import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="RVU Tracker", layout="centered")

# Load RVU CPT data
@st.cache_data
def load_rvu_data():
    df = pd.read_csv("rvu_codes.csv")
    df["Display"] = df["CPT"] + " — " + df["Description"]
    return df

rvu_df = load_rvu_data()

st.title("📊 RVU Tracker")

# User input
st.subheader("Enter Procedure")
entry_date = st.date_input("Date of Service", date.today())
selected_display = st.selectbox("Select CPT Code + Description", rvu_df["Display"])
qty = st.number_input("Quantity", min_value=1, value=1)

# RVU lookup
selected_row = rvu_df[rvu_df["Display"] == selected_display]
cpt_code = selected_row["CPT"].values[0]
description = selected_row["Description"].values[0]
rvu = float(selected_row["wRVU"].values[0])
total_rvu = rvu * qty

st.write(f"**{qty} x {cpt_code} ({description}) = {total_rvu:.2f} wRVUs**")

# Logging entries
if "log" not in st.session_state:
    st.session_state.log = []

if st.button("Log Entry"):
    st.session_state.log.append({
        "Date": entry_date,
        "Week": entry_date.strftime("%Y-W%U"),
        "Month": entry_date.strftime("%B %Y"),
        "CPT": cpt_code,
        "Description": description,
        "Qty": qty,
        "wRVU": rvu,
        "Total RVUs": total_rvu
    })
    st.success("Entry logged!")

# Optional RVU goal
with st.expander("🎯 Monthly RVU Goal (Optional)"):
    rvu_goal = st.number_input("Set your RVU goal for the month", min_value=0, value=1000)

# Show log
if st.session_state.log:
    st.subheader("📋 RVU Log")
    df_log = pd.DataFrame(st.session_state.log)
    df_log["Date"] = pd.to_datetime(df_log["Date"])
    st.dataframe(df_log)

    # Total RVUs
    total = df_log["Total RVUs"].sum()
    st.metric("Total wRVUs Logged", total)

    # Grouped Summaries
    st.subheader("📆 Summary by Week")
    weekly = df_log.groupby("Week")["Total RVUs"].sum().reset_index()
    st.dataframe(weekly)

    st.subheader("📅 Summary by Month")
    monthly = df_log.groupby("Month")["Total RVUs"].sum().reset_index()
    st.dataframe(monthly)

    # Goal progress
    if rvu_goal > 0:
        current_month = date.today().strftime("%B %Y")
        month_total = df_log[df_log["Month"] == current_month]["Total RVUs"].sum()
        percent = (month_total / rvu_goal) * 100
        st.metric(label=f"📈 Progress for {current_month}", value=f"{month_total:.2f} RVUs", delta=f"{percent:.1f}% of goal")

# -----------------------------------------
# 🧮 RVU Goal Calculator
# -----------------------------------------
st.subheader("🧮 RVU Goal Calculator")

calc_goal = st.number_input("Enter RVU Goal (Weekly or Monthly)", min_value=0, value=250)

st.markdown("Select procedures to build your plan:")

calc_df = rvu_df.copy()
calc_df["Include"] = False

for i in range(len(calc_df)):
    row = calc_df.iloc[i]
    label = f"{row['CPT']} — {row['Description']} ({row['wRVU']} wRVU)"
    calc_df.at[i, "Include"] = st.checkbox(label, key=f"calc_{row['CPT']}")

# Filter selected
selected_calc_df = calc_df[calc_df["Include"] == True]

if not selected_calc_df.empty:
    st.subheader("📈 Estimated Procedure Counts Needed")
    target_rows = []

    for _, row in selected_calc_df.iterrows():
        num_needed = int(calc_goal // row["wRVU"])
        target_rows.append({
            "CPT": row["CPT"],
            "Description": row["Description"],
            "wRVU per": row["wRVU"],
            "Qty Needed": num_needed,
            "Total RVUs": num_needed * row["wRVU"]
        })

    st.dataframe(pd.DataFrame(target_rows))

    total_possible = sum([r["Total RVUs"] for r in target_rows])
    st.markdown(f"**Combined RVUs: {total_possible:.2f}** vs Target: **{calc_goal}**")
else:
    st.info("Select at least one procedure to calculate.")
