import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from datetime import timedelta

# Set page config (optional)
st.set_page_config(page_title="Overhaul Forecast Dashboard", layout="wide")

# ===================== SIDEBAR: USER-DEFINED PARAMETERS =====================

st.sidebar.header("User-Defined Values")

# File path and sheet name (you can modify these; alternatively use st.file_uploader)
file_path = st.sidebar.text_input(
    "Excel File Path", 
    r"E:\OneDrive - Fauji Fertilizer Company Ltd\AMMONIA MACHINERY\KGT Running speed.xlsx"
)
sheet_name = st.sidebar.text_input("Sheet Name", "RunningHrs")

# Operating thresholds
fired_speed_threshold = st.sidebar.number_input(
    "Fired Speed Threshold (RPM)", value=1100
)
max_fired_hours = st.sidebar.number_input(
    "Max Fired Hours for Overhaul", value=84000
)

# Maintenance Factor graph data (starts per fired hour vs maintenance factor)
x = np.array([0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
y = np.array([1.1, 1.3, 1.45, 1.7, 2.1, 2.9, 4.0, 5.0])

display_chart = st.sidebar.checkbox("Show Trend Chart", value=True)

# ===================== DATA LOADING AND PREPARATION =====================

@st.cache_data
def load_data(file_path, sheet_name, fired_speed_threshold):
    # Read Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    # Convert date column and sort
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)
    # Mark fired condition
    df['Fired'] = df['AASPEED.PV/SIG'] > fired_speed_threshold
    # Return DataFrame
    return df

try:
    df = load_data(file_path, sheet_name, fired_speed_threshold)
except Exception as e:
    st.error(f"Error loading data: {e}")

st.subheader("Raw Data Preview")
st.dataframe(df.head(10))

# ===================== FIRING EVENT DETECTION =====================

# Detect state transitions (start/stop)
df['Change'] = df['Fired'] != df['Fired'].shift()
transitions = df[df['Change']]

# Extract firing start and stop timestamps
firing_starts = transitions[transitions['Fired']]['Date'].reset_index(drop=True)
firing_stops = transitions[~transitions['Fired']]['Date'].reset_index(drop=True)

# Create a firing summary table
firing_summary = pd.DataFrame({
    'Firing Start': firing_starts,
    'Firing Stop': firing_stops.shift(-1)  # match stop to start; last row may be dropped
})
firing_summary['Fired Duration (hrs)'] = (
    firing_summary['Firing Stop'] - firing_summary['Firing Start']
).dt.total_seconds() / 3600
firing_summary.dropna(inplace=True)

st.subheader("Firing Summary")
st.dataframe(firing_summary)

# ===================== EOH CALCULATION =====================

# Total Fired Hours and EOH calculation based on the firing summary
total_fired_hours = firing_summary['Fired Duration (hrs)'].sum()
number_of_starts = len(firing_summary)

# Create interpolation function for maintenance factor
mf_interp = interp1d(x, y, kind='linear', fill_value='extrapolate')
R = number_of_starts / total_fired_hours if total_fired_hours > 0 else 0
maintenance_factor = float(mf_interp(R))
EOH = total_fired_hours * maintenance_factor

# ===================== OVERHAUL FORECASTING =====================

# 1. Startup date: first time the machine was fired after last overhaul
startup_date = df[df['Fired']].iloc[0]['Date']

# 2. Expected OH Date (Calendar Time) = Startup Date + 84000 fired hours (as calendar hours)
expected_oh_date_calendar = startup_date + timedelta(hours=max_fired_hours)

# 3. Expected OH Date (EOH Adjusted) = Calendar OH date + (EOH - Fired Hours)
extra_eoh_hours = EOH - total_fired_hours
expected_oh_date_eoh = expected_oh_date_calendar + timedelta(hours=extra_eoh_hours)

# 4. Projected OH Date based on trend: extrapolate current fired-hour accumulation
days_since_start = (df['Date'].max() - startup_date).days + 1
avg_fired_hours_per_day = total_fired_hours / days_since_start if days_since_start > 0 else 0
remaining_fired_hours = max_fired_hours - total_fired_hours
days_to_reach_oh = remaining_fired_hours / avg_fired_hours_per_day if avg_fired_hours_per_day > 0 else 0
projected_oh_date = df['Date'].max() + timedelta(days=days_to_reach_oh)

# ===================== FINAL SUMMARY TABLE =====================

final_summary_df = pd.DataFrame({
    "Metric": [
        "First Firing Date after Overhauling",
        "Expected OH Date (Calendar Time)",
        "Expected OH Date (EOH Adjusted)",
        "Projected OH Date (Fired Hours Trend)"
    ],
    "Value": [
        startup_date.date().isoformat(),
        expected_oh_date_calendar.date().isoformat(),
        expected_oh_date_eoh.date().isoformat(),
        projected_oh_date.date().isoformat()
    ]
})

st.subheader("Overhaul Forecast Summary")
st.dataframe(final_summary_df)

# ===================== OPTIONAL: CHARTS =====================
if display_chart:
    st.subheader("Trend Chart: Machine Speed Over Time")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['Date'], df['AASPEED.PV/SIG'], color='blue', label='Speed')
    ax.set_xlabel("Date")
    ax.set_ylabel("Speed (RPM)")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Fired Duration per Event")
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.bar(firing_summary['Firing Start'].dt.date.astype(str), firing_summary['Fired Duration (hrs)'])
    ax2.set_xlabel("Firing Event Start Date")
    ax2.set_ylabel("Duration (hrs)")
    st.pyplot(fig2)

# ===================== DISPLAY CALCULATED VALUES =====================
st.subheader("Calculated Values")
st.markdown(f"**Total Fired Hours:** {total_fired_hours:.2f} hrs")
st.markdown(f"**Number of Starts:** {number_of_starts}")
st.markdown(f"**Maintenance Factor:** {maintenance_factor:.2f}")
st.markdown(f"**Equivalent Operating Hours (EOH):** {EOH:.2f} hrs")
st.markdown(f"**Avg Fired Hrs/Day:** {avg_fired_hours_per_day:.2f} hrs")
