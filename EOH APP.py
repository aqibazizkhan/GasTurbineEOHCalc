import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from datetime import datetime

st.set_page_config(page_title="Gas Turbine EOH Calculator", layout="centered")

st.title("🛠️ Gas Turbine EOH Calculator")
st.markdown("""
Upload an Excel file containing date/time and machine RPM to calculate:
- Fired hours
- Number of starts
- Maintenance factor (interpolated)
- Equivalent Operating Hours (EOH)
""")

# User input
fired_speed_threshold = st.number_input("Fired Speed Threshold (RPM)", value=1100)
max_fired_hours = st.number_input("Maximum Allowed Fired Hours", value=84000)

uploaded_file = st.file_uploader("📤 Upload Excel File", type=["xlsx"])

if uploaded_file:
    try:
        sheet_names = pd.ExcelFile(uploaded_file).sheet_names
        sheet_name = st.selectbox("Select Sheet", sheet_names)

        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

        if df.shape[1] < 2:
            st.error("The uploaded file must contain at least two columns: Date and RPM.")
        else:
            # Rename for standardization
            df = df.rename(columns={df.columns[0]: 'Date', df.columns[1]: 'RPM'})
            df['Date'] = pd.to_datetime(df['Date'])
            df['Fired'] = df['RPM'] > fired_speed_threshold
            df = df.sort_values('Date')

            # Detect transitions
            df['Change'] = df['Fired'] != df['Fired'].shift()
            transitions = df[df['Change']]

            # Extract starts and stops
            firing_starts = transitions[transitions['Fired'] == True]['Date'].reset_index(drop=True)
            firing_stops = transitions[transitions['Fired'] == False]['Date'].reset_index(drop=True)

            firing_summary = pd.DataFrame({
                'Firing Start': firing_starts,
                'Firing Stop': firing_stops.shift(-1)
            })

            firing_summary['Fired Duration (hrs)'] = (
                firing_summary['Firing Stop'] - firing_summary['Firing Start']
            ).dt.total_seconds() / 3600

            firing_summary.dropna(inplace=True)

            st.subheader("⏱️ Firing Start/Stop Summary")
            st.dataframe(firing_summary)

            # Maintenance factor interpolation
            x = np.array([0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
            y = np.array([1.1, 1.3, 1.45, 1.7, 2.1, 2.9, 4.0, 5.0])
            mf_interp = interp1d(x, y, kind='linear', fill_value='extrapolate')

            total_fired_hours = firing_summary['Fired Duration (hrs)'].sum()
            number_of_starts = len(firing_summary)
            R = number_of_starts / total_fired_hours if total_fired_hours > 0 else 0
            maintenance_factor = float(mf_interp(R))
            EOH = total_fired_hours * maintenance_factor

            st.subheader("📊 EOH Summary")
            st.markdown(f"""
            - **Total Fired Hours:** `{total_fired_hours:.2f}` hrs  
            - **Number of Starts:** `{number_of_starts}`  
            - **Starts per Fired Hour (R):** `{R:.4f}`  
            - **Maintenance Factor:** `{maintenance_factor:.2f}`  
            - **Equivalent Operating Hours (EOH):** `{EOH:.2f}` hrs  
            """)

            # Progress toward max limit
            percent_used = (EOH / max_fired_hours) * 100
            st.progress(min(percent_used, 100), text=f"{percent_used:.1f}% of {max_fired_hours} hrs used")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

else:
    st.info("📎 Please upload an Excel file to begin.")
