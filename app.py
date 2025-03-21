import streamlit as st
import pandas as pd
from datetime import date

# Load CPT → wRVU data
@st.cache_data
def load_rvu_data():
    return pd.read_csv("rvu_codes.csv")

rvu_df = load_rvu_data()

st.title("📊 RVU Tracker")

# Entry Form
st.subheader("Enter RVU Entry")
entry_date = st.date_input("Date of Service", date.today())
cpt_code = st.text_input("CPT Code (e.g. 99205)").strip()
qty = st.number_input("Quantity", min_value=1, value=1)

# Lookup and calculate
if cpt_code in rvu_df['CPT'].values:
    rvu = float(rvu_df[rvu_df['CPT'] == cpt_code]['wRVU'].values[0])
    total_rvu = rvu * qty
    st.success(f"{qty} x {cpt_code} = {total_rvu:.2f} wRVUs")
else:
    rvu = 0
    total_rvu = 0
    st.warning("CPT code not found. Add it to rvu_codes.csv.")

# Logging entries
if 'log' not in st.session_state:
    st.session_state.log = []

if st.button("Log Entry"):
    st.session_state.log.append({
        'Date': entry_date,
        'CPT': cpt_code,
        'Qty': qty,
        'wRVU': rvu,
        'Total wRVU': total_rvu
    })

if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    st.subheader("RVU Log")
    st.dataframe(df)
    st.metric("Total wRVUs", df['Total wRVU'].sum())
