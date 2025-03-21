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

# User input section
st.subheader("Enter Procedure")
entry_date = st.date_input("Date of Service", date.today())
selected_display = st.selectbox("Select CPT Code + Description", rvu_df["Display"])

qty = st.number_input("Quantity", min_value=1, value=1)

# Get CPT and RVU
selected_row = rvu_df[rvu_df["Display"] == selected_display]
cpt_code = selected_row["CPT"].values[0]
description = selected_row["Description"].values[0]
rvu = float(selected_row["wRVU"].values[0])
total_rvu = rvu * qty

st.write(f"**{qty} x {cpt_code} ({description}) = {total_rvu:.2f} wRVUs**")

# Initialize log
if "log" not in st.session_state:
    st.session_state.log = []

# Save entry
if st.button("Log Entry"):
    st.session_state.log.append({
        "Date": entry_date,
        "CPT": cpt_code,
        "Description": description,
        "Qty": qty,
        "wRVU": rvu,
        "Total RVUs": total_rvu
    })
    st.success("Entry logged!")

# Display log
if st.session_state.log:
    st.subheader("📋 RVU Log")
    df_log = pd.DataFrame(st.session_state.log)
    st.dataframe(df_log)
    st.metric("Total wRVUs Logged", df_log["Total RVUs"].sum())
