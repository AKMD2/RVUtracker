
import streamlit as st
import pandas as pd
from datetime import date
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="RVU Tracker", layout="centered")

spreadsheet_name = 'RVU_Sheet'
sheet_name = 'Sheet1'

def connect_to_gsheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive']
    creds_dict = {k: v for k, v in st.secrets["gspread"].items()}
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    try:
        worksheet = client.open(spreadsheet_name).worksheet(sheet_name)
        return worksheet
    except Exception as e:
        st.error(f"❌ Google Sheets API error: {e}")
        st.stop()

worksheet = connect_to_gsheet()

@st.cache_data
def load_rvu_data():
    df = pd.read_csv("rvu_codes.csv")
    additions = {
        "93571": {"wRVU": 1.00, "Description": "Instantaneous wave-free ratio (iFR) (Cath/PCI)"},
        "37184": {"wRVU": 8.00, "Description": "Pulmonary Thrombectomy (Cath/PCI)"}
    }
    for cpt, val in additions.items():
        if cpt not in df["CPT"].values:
            df.loc[len(df)] = [cpt, val["wRVU"], val["Description"]]
    df["Display"] = df["CPT"] + " — " + df["Description"]
    return df

@st.cache_data
def load_log_data():
    rows = worksheet.get_all_records()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
    return df

def save_log_entry(entries):
    df = load_log_data()
    new_df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
    worksheet.clear()
    worksheet.update([new_df.columns.values.tolist()] + new_df.values.tolist())

rvu_df = load_rvu_data()
log_df = load_log_data()

st.sidebar.title("👤 User")
username = st.sidebar.text_input("Enter your name or initials", value="Anonymous")

st.title("📊 RVU Tracker (Google Sheets Enabled)")

st.subheader("Enter Multiple Procedures for a Single Case")
entry_date = st.date_input("Date of Service", date.today())
selected_displays = st.multiselect("Select CPT Code(s) + Description(s)", rvu_df["Display"])

st.markdown("### ✅ Procedure Quantities")
quantities = {}
cols = st.columns(2)
for i, item in enumerate(selected_displays):
    cpt = rvu_df[rvu_df["Display"] == item]["CPT"].values[0]
    with cols[i % 2]:
        quantities[cpt] = st.number_input(f"{item}", min_value=1, value=1, key=f"qty_{cpt}")

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
    st.success("All procedures logged to Google Sheets!")

with st.expander("🎯 Monthly RVU Goal (Optional)"):
    rvu_goal = st.number_input("Set your RVU goal for the month", min_value=0, value=1000)

is_admin = username.lower() == "admin"
if is_admin and not log_df.empty:
    st.warning("🔒 Admin Mode Enabled: Viewing all users’ RVUs")
    user_list = sorted(log_df["User"].unique())
    selected_user = st.selectbox("Filter by user", options=["All Users"] + user_list)
    df_user = log_df.copy() if selected_user == "All Users" else log_df[log_df["User"] == selected_user]
else:
    df_user = log_df[log_df["User"] == username]

if not df_user.empty:
    st.subheader("📋 RVU Log" + (" (All Users)" if is_admin else ""))
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

    st.subheader("📥 Export RVU Log")
    csv = df_user.to_csv(index=False).encode("utf-8")
    export_name = f"rvu_log_all_users.csv" if is_admin and selected_user == "All Users" else f"rvu_log_{username}.csv"
    st.download_button("Download as CSV", data=csv, file_name=export_name, mime="text/csv")
