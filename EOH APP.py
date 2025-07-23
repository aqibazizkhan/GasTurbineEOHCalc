import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from datetime import datetime

# Constants
fired_speed_threshold = 1100
max_fired_hours = 84000

# Maintenance Factor Graph Data
x = np.array([0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
y = np.array([1.1, 1.3, 1.45, 1.7, 2.1, 2.9, 4.0, 5.0])
mf_interp = interp1d(x, y, kind='linear', fill_value='extrapolate')

# Streamlit App
st.set_page_config(page_title="EOH Calculator", layout="centered")
st.title("🔧 Equivalent Operating Hours (EOH) Calculator")

uploaded_file = st.file_uploader("📤 Upload Excel File", type=["xlsx"])

if uploaded_file:
    try:
        sheet_name = st.text_input("Enter Sheet Name", value="RunningHrs")
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

        st.success("✅ File uploaded successfully.")

        # Convert date column
        df['Date'] = pd.to_datetime(df.iloc[:, 0])
        rpm_column = df.columns[1]  # 2nd column is RPM
        df['Fired'] = df[rpm_column] > fired_speed_threshold
        df.sort_values('Date', inplace=True)
        df['Change'] = df['Fired'] != df['Fired'].shift()

        # Start/Stop
        transitions = df[df['Change']]
        firing_starts = transitions[transitions['Fired'] == True]['Date'].reset_index(drop=True)
        firing_stops = transitions[transitions['Fired'] == False]['Date'].reset_index(drop=True)

        # Summary Table
        firing_summary = pd.DataFrame({
            'Firing Start': firing_starts,
            'Firing Stop': firing_stops.shift(-1)
        })
        firing_summary['Fired Duration (hrs)'] = (
            firing_summary['Firing Stop'] - firing_summary['Firing Start']
        ).dt.total_seconds() / 3600
        firing_summary.dropna(inplace=True)

        # Calculations
        total_fired_hours = firing_summary['Fired Duration (hrs)'].sum()
        number_of_starts = len(firing_summary)
        R = number_of_starts / total_fired_hours if total_fired_hours > 0 else 0
        maintenance_factor = float(mf_interp(R))
        EOH = total_fired_hours * maintenance_factor

        # Display results
        st.subheader("📈 Results")
        st.metric("Total Fired Hours", f"{total_fired_hours:.2f} hrs")
        st.metric("Number of Starts", number_of_starts)
        st.metric("Starts per Fired Hour (R)", f"{R:.4f}")
        st.metric("Maintenance Factor", f"{maintenance_factor:.2f}")
        st.metric("Equivalent Operating Hours (EOH)", f"{EOH:.2f} hrs")

        # Show progress bar for EOH utilization
        st.subheader("📊 EOH Utilization")
        progress_value = min(EOH / max_fired_hours, 1.0)
        st.progress(progress_value)
        st.caption(f"Usage: {EOH:.2f} / {max_fired_hours} hrs")

        # Show table if checked
        if st.checkbox("Show Firing Events Table"):
            st.dataframe(firing_summary)

        # Optional: plot RPM over time
        st.subheader("🌀 RPM Trend")
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(df['Date'], df[rpm_column], label="RPM", color='blue')
        ax.axhline(fired_speed_threshold, color='red', linestyle='--', label='Fired Threshold')
        ax.set_xlabel("Date/Time")
        ax.set_ylabel("RPM")
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
