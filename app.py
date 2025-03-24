
import streamlit as st
import pandas as pd
from datetime import date
import altair as alt
import os

st.set_page_config(page_title="RVU Tracker", layout="centered")

@st.cache_data
def load_rvu_data():
    df = pd.read_csv("rvu_codes.csv")
    if "93571" not in df["CPT"].values:
        df.loc[len(df)] = ["93571", 1.00, "Instantaneous wave-free ratio (iFR) (Cath/PCI)"]
    df["Display"] = df["CPT"] + " — " + df["Description"]
    return df

def load_log_data():
    if os.path.exists("rvu_log.csv"):
        return pd.read_csv("rvu_log.csv", parse_dates=["Date"])
    else:
        return pd.DataFrame(columns=["User", "Date", "Week", "Month", "CPT", "Description", "Qty", "wRVU", "Total RVUs"])

def save_log_entry(entry):
    df = load_log_data()
    df = pd.concat([df, pd.DataFrame(entry)], ignore_index=True)
    df.to_csv("rvu_log.csv", index=False)

rvu_df = load_rvu_data()
log_df = load_log_data()

# Multi-user support
st.sidebar.title("👤 User")
username = st.sidebar.text_input("Enter your name or initials", value="Anonymous")

st.title("📊 RVU Tracker")

# User input: select multiple CPTs
st.subheader("Enter Multiple Procedures for a Single Case")
entry_date = st.date_input("Date of Service", date.today())
selected_displays = st.multiselect("Select CPT Code(s) + Description(s)", rvu_df["Display"])

# Quantity inputs
st.markdown("### ✅ Procedure Quantities")
quantities = {}
cols = st.columns(2)
for i, item in enumerate(selected_displays):
    cpt = rvu_df[rvu_df["Display"] == item]["CPT"].values[0]
    with cols[i % 2]:
        quantities[cpt] = st.number_input(f"{item}", min_value=1, value=1, key=f"qty_{cpt}")

# Log selected procedures
if st.button("Log All Selected"):
    new_entries = []
    for item in selected_displays:
        row = rvu_df[rvu_df["Display"] == item].iloc[0]
        qty = quantities[row["CPT"]]
        total_rvu = qty * float(row["wRVU"])
        new_entries.append({
            "User": username,
            "Date": entry_date,
            "Week": entry_date.strftime("%Y-W%U"),
            "Month": entry_date.strftime("%B %Y"),
            "CPT": row["CPT"],
            "Description": row["Description"],
            "Qty": qty,
            "wRVU": row["wRVU"],
            "Total RVUs": total_rvu
        })
    save_log_entry(new_entries)
    st.success("All procedures logged!")

# Optional goal
with st.expander("🎯 Monthly RVU Goal (Optional)"):
    rvu_goal = st.number_input("Set your RVU goal for the month", min_value=0, value=1000)

# Display user-specific log
df_user = log_df[log_df["User"] == username]
if not df_user.empty:
    st.subheader("📋 Your RVU Log")
    st.dataframe(df_user)

    total = df_user["Total RVUs"].sum()
    st.metric("Total wRVUs Logged", total)

    st.subheader("📆 Summary by Week")
    weekly = df_user.groupby("Week")["Total RVUs"].sum().reset_index()
    st.dataframe(weekly)

    st.subheader("📅 Summary by Month")
    monthly = df_user.groupby("Month")["Total RVUs"].sum().reset_index()
    st.dataframe(monthly)

    if rvu_goal > 0:
        current_month = date.today().strftime("%B %Y")
        month_total = df_user[df_user["Month"] == current_month]["Total RVUs"].sum()
        percent = (month_total / rvu_goal) * 100
        st.metric(label=f"📈 Progress for {current_month}", value=f"{month_total:.2f} RVUs", delta=f"{percent:.1f}% of goal")

    st.subheader("📈 Weekly RVU Trend")
    weekly_chart = alt.Chart(weekly).mark_line(point=True).encode(x="Week", y="Total RVUs").properties(width=600)
    st.altair_chart(weekly_chart)

    st.subheader("📆 Monthly RVU Trend")
    monthly_chart = alt.Chart(monthly).mark_bar().encode(x="Month", y="Total RVUs").properties(width=600)
    st.altair_chart(monthly_chart)

    st.subheader("📥 Export Your RVU Log")
    csv = df_user.to_csv(index=False).encode("utf-8")
    st.download_button("Download as CSV", data=csv, file_name=f"rvu_log_{username}.csv", mime="text/csv")
