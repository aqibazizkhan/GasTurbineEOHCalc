# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from datetime import datetime, timedelta

st.set_page_config(page_title="Gas Turbine EOH Calculator", layout="wide")
st.title("🛠️ Gas Turbine EOH Calculator & Overhaul Predictor")

st.markdown("""
This tool calculates **Equivalent Operating Hours (EOH)** and predicts gas turbine **overhaul dates** 
based on fired hours, EOH readings, and firing date after last overhaul.
Upload your Excel file to get started.
""")

uploaded_file = st.file_uploader("📤 Upload Excel file with 'Date', 'Fired Hours', 'EOH' columns:", type=['xlsx'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        st.success("✅ File loaded successfully!")

        required_columns = {'Date', 'Fired Hours', 'EOH'}
        if not required_columns.issubset(df.columns):
            st.error(f"Missing columns: {required_columns - set(df.columns)}")
            st.stop()

        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')

        st.subheader("📊 Data Preview")
        st.dataframe(df.head())

        # User input for last overhaul firing date and hours at overhaul
        st.sidebar.header("🔧 Settings")
        first_firing_date = st.sidebar.date_input("First Firing Date after Overhaul:", value=df['Date'].min().date())
        fired_hours_at_oh = st.sidebar.number_input("Fired Hours at Overhaul (typically 0):", value=0.0)
        eoh_at_oh = st.sidebar.number_input("EOH at Overhaul (typically 0):", value=0.0)

        # Latest values
        latest_date = df['Date'].iloc[-1]
        latest_fired = df['Fired Hours'].iloc[-1]
        latest_eoh = df['EOH'].iloc[-1]

        # Calendar-based OH
        calendar_oh_date = datetime.combine(first_firing_date, datetime.min.time()) + timedelta(hours=84000)

        # EOH-based OH
        remaining_eoh = 84000 - (latest_eoh - eoh_at_oh)
        projected_eoh_date = latest_date + timedelta(hours=remaining_eoh)

        # Fired Hours based projection using linear interpolation
        df['Cumulative Fired Hours'] = df['Fired Hours'] - df['Fired Hours'].iloc[0] + fired_hours_at_oh
        interp = interp1d(df['Cumulative Fired Hours'], df['Date'].astype(np.int64), fill_value="extrapolate")
        predicted_timestamp = interp(84000)
        projected_fired_oh_date = pd.to_datetime(predicted_timestamp)

        # Display results
        st.subheader("📅 Predicted Overhaul Dates")
        col1, col2, col3 = st.columns(3)
        col1.metric("Calendar Based", calendar_oh_date.date())
        col2.metric("EOH Based", projected_eoh_date.date())
        col3.metric("Fired Hours Based", projected_fired_oh_date.date())

        # Plot
        st.subheader("📈 Trend: EOH vs Date")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['Date'], df['EOH'], label='EOH', color='blue')
        ax.axhline(84000, color='red', linestyle='--', label='Target EOH')
        ax.axvline(projected_eoh_date, color='green', linestyle='--', label='EOH Projected Date')
        ax.set_ylabel("EOH")
        ax.set_xlabel("Date")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()
else:
    st.info("👈 Upload an Excel file to get started.")
