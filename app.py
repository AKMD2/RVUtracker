
import streamlit as st
import pandas as pd
from datetime import date
import altair as alt

st.set_page_config(page_title="RVU Tracker", layout="centered")

# Load RVU CPT data
@st.cache_data
def load_rvu_data():
    df = pd.read_csv("rvu_codes.csv")
    df["Display"] = df["CPT"] + " — " + df["Description"]
    return df

rvu_df = load_rvu_data()

# Multi-user input
st.sidebar.title("👤 User")
username = st.sidebar.text_input("Enter your name or initials", value="Anonymous")

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
        "User": username,
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
    df_user = df_log[df_log["User"] == username]
    st.dataframe(df_user)

    # Total RVUs
    total = df_user["Total RVUs"].sum()
    st.metric("Total wRVUs Logged", total)

    # Grouped Summaries
    st.subheader("📆 Summary by Week")
    weekly = df_user.groupby("Week")["Total RVUs"].sum().reset_index()
    st.dataframe(weekly)

    st.subheader("📅 Summary by Month")
    monthly = df_user.groupby("Month")["Total RVUs"].sum().reset_index()
    st.dataframe(monthly)

    # Goal progress
    if rvu_goal > 0:
        current_month = date.today().strftime("%B %Y")
        month_total = df_user[df_user["Month"] == current_month]["Total RVUs"].sum()
        percent = (month_total / rvu_goal) * 100
        st.metric(label=f"📈 Progress for {current_month}", value=f"{month_total:.2f} RVUs", delta=f"{percent:.1f}% of goal")

    # Trend Charts
    st.subheader("📈 Weekly RVU Trend")
    weekly_chart = alt.Chart(weekly).mark_line(point=True).encode(
        x="Week", y="Total RVUs"
    ).properties(width=600)
    st.altair_chart(weekly_chart)

    st.subheader("📆 Monthly RVU Trend")
    monthly_chart = alt.Chart(monthly).mark_bar().encode(
        x="Month", y="Total RVUs"
    ).properties(width=600)
    st.altair_chart(monthly_chart)

    # Export to CSV
    st.subheader("📥 Export RVU Log")
    csv = df_user.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"rvu_log_{username}.csv",
        mime="text/csv"
    )

# RVU Goal Planner with Sliders
st.subheader("🧮 RVU Goal Planner with Sliders")
calc_goal = st.number_input("Enter RVU Goal (Weekly or Monthly)", min_value=0, value=250)
st.markdown("**Select procedures and adjust sliders to build your plan:**")

calc_df = rvu_df.copy()
calc_df["Include"] = False

for i in range(len(calc_df)):
    row = calc_df.iloc[i]
    label = f"{row['CPT']} — {row['Description']} ({row['wRVU']} wRVU)"
    calc_df.at[i, "Include"] = st.checkbox(label, key=f"slider_{row['CPT']}")

selected_calc_df = calc_df[calc_df["Include"] == True]

if not selected_calc_df.empty:
    st.subheader("📈 RVU Totals Based on Your Plan")
    slider_results = []

    for _, row in selected_calc_df.iterrows():
        max_qty = int(calc_goal // row["wRVU"]) + 5
        qty = st.slider(f"{row['CPT']} — {row['Description']}", 0, max_qty, 0)
        subtotal = qty * row["wRVU"]
        slider_results.append({
            "CPT": row["CPT"],
            "Description": row["Description"],
            "Qty Planned": qty,
            "wRVU per": row["wRVU"],
            "Total RVUs": subtotal
        })

    slider_df = pd.DataFrame(slider_results)
    st.dataframe(slider_df)

    total_slider_rvus = slider_df["Total RVUs"].sum()
    delta = total_slider_rvus - calc_goal
    st.metric(label="📊 Planned Total RVUs", value=f"{total_slider_rvus:.2f}", delta=f"{delta:+.2f} from goal")
else:
    st.info("Select procedures above to enable sliders.")
