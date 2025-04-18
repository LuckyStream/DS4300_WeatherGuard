import streamlit as st
import boto3
import pymysql
import pandas as pd
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
import io  

# -------- CONFIGURATION -------- #
BUCKET_NAME = 'boston-weather-raw'
REGION = 'us-east-2'

RDS_HOST = "weather-db.c56ekmoqeysw.us-east-2.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "123456789"
DB_NAME = "weather"

# -------- FUNCTION TO LOAD LOTTIE ANIMATION -------- #
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# -------- PAGE SETUP -------- #
st.set_page_config(page_title="WeatherGuard", layout="wide")

# -------- CUSTOM CSS FOR BUTTONS/EXPANDERS -------- #
st.markdown('''
<style>
/* Style ALL Streamlit buttons */
div.stButton > button {
    background-color: #b3cde0;    /* Light bluish-gray background */
    color: #000000;              /* Black text */
    border: none;                /* Remove default border */
    border-radius: 0.25rem;      /* Slightly rounded corners */
    height: 2.5rem;              /* Increase height */
    padding: 0.5rem 1rem;        /* Some padding */
    font-size: 1rem;             /* Increase font size */
    font-weight: 600;            /* Make text a bit bolder */
    cursor: pointer;             /* Pointer on hover */
}

div.stButton > button:hover {
    background-color: #92b1d0;    /* Darker shade on hover */
    color: #ffffff;              /* White text on hover */
}

/* Style ALL Streamlit download buttons similarly */
div.stDownloadButton > button {
    background-color: #b3cde0;
    color: #000000;
    border: none;
    border-radius: 0.25rem;
    height: 2.5rem;
    padding: 0.5rem 1rem;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
}

div.stDownloadButton > button:hover {
    background-color: #92b1d0;
    color: #ffffff;
}

/* Style for Streamlit expanders */
.streamlit-expanderHeader {
    background-color: #b3cde0;  /* Background color for the expander header */
    color: #000000;
    font-weight: 600;
}
</style>
''', unsafe_allow_html=True)

st.markdown("""
    <style>
    .main {
        background-color: #f7f9fa;
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# -------- SIDEBAR SECTION -------- #
st.sidebar.title("About WeatherGuard")
st.sidebar.markdown("""
**WeatherGuard** is a Boston Weather Anomaly Detection and Monitoring System.
- Upload your **CSV file** containing daily weather records.
- Our pipeline processes the file to detect anomalies in weather data.
- You can then explore the summary metrics, anomalies, and temperature trends in real time.

**CSV Requirements**:
- Must be a valid CSV file with columns like `record_date`, `temp_avg`, `anomaly`, etc.
- The app expects one row per date.
""")

# -------- HEADER SECTION -------- #
col1, col2 = st.columns([1.5, 3.5])
with col1:
    st.image("weather.png", use_container_width=True)

with col2:
    st.title("WeatherGuard")
    st.write("Boston Weather Anomaly Detection and Monitoring System")

tab1, tab2 = st.tabs(["Data Upload", "Data Analysis"])

# -------- TAB 1: Data Upload -------- #
with tab1:
    st.header("Upload Weather CSV File")
    uploaded_file = st.file_uploader("Select a CSV file to upload to S3", type="csv")

    if uploaded_file:
        s3 = boto3.client('s3', region_name=REGION)
        try:
            s3.upload_fileobj(uploaded_file, BUCKET_NAME, uploaded_file.name)
            st.success(f"File '{uploaded_file.name}' uploaded successfully. Lambda is processing the data.")
            # lottie_success = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_dy7uMy.json")
            # if lottie_success:
            #     st_lottie(lottie_success, speed=1, width=300, key="upload_success")
            # else:
            #     st.info("Upload succeeded, but animation could not be loaded.")
        except Exception as e:
            st.error("Upload failed.")
            st.text(str(e))

# -------- TAB 2: Data Analysis -------- #
with tab2:
    st.header("Weather Data Analysis")

    try:
        connection = pymysql.connect(
            host=RDS_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM weather_data ORDER BY record_date DESC")
            result = cursor.fetchall()
            df = pd.DataFrame(result)

        if df.empty:
            st.info("No data available. Please upload a CSV file to begin analysis (or re-check your database).")
        else:
            df["record_date"] = pd.to_datetime(df["record_date"])

            # -------- DATE RANGE FILTER -------- #
            min_date = df["record_date"].min().date()
            max_date = df["record_date"].max().date()

            st.subheader("Filter by Date Range")
            start_date, end_date = st.date_input(
                "Select Start and End Date",
                value=[min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )

            if isinstance(start_date, list):
                start_date, end_date = start_date

            if start_date > end_date:
                st.error("Error: Start date must be before end date.")
            else:
                # -------- ANOMALY FILTER -------- #
                st.subheader("Filter by Anomaly Type")
                all_anomalies = ["All"] + sorted(df["anomaly"].unique())
                selected_anomaly = st.selectbox("Select an anomaly type:", all_anomalies)

                mask_date = (df["record_date"].dt.date >= start_date) & (df["record_date"].dt.date <= end_date)
                filtered_df = df.loc[mask_date].copy()

                if selected_anomaly != "All":
                    filtered_df = filtered_df[filtered_df["anomaly"] == selected_anomaly]

                if filtered_df.empty:
                    st.warning("No data found for the selected filters.")
                else:
                    total_rows = len(filtered_df)
                    anomalies_count = filtered_df[filtered_df["anomaly"] != "Normal"].shape[0]

                    c1, c2 = st.columns(2)
                    c1.metric("Total Records (Filtered)", f"{total_rows}")
                    c2.metric("Anomalies Detected", f"{anomalies_count}")

                    buffer = io.StringIO()
                    filtered_df.to_csv(buffer, index=False)
                    csv_data = buffer.getvalue()
                    st.download_button(
                        label="Download Filtered Data (CSV)",
                        data=csv_data,
                        file_name="filtered_weather_data.csv",
                        mime="text/csv"
                    )

                    with st.expander("Show Filtered Data Table"):
                        st.dataframe(filtered_df)

                    # Detailed Temperature Statistics
                    with st.expander("Detailed Temperature Statistics"):
                        if "temp_avg" in filtered_df.columns:
                            stats = filtered_df["temp_avg"].describe()
                            st.write("**Basic Statistics for `temp_avg`:**")
                            st.table(stats.to_frame().T)
                        else:
                            st.info("No `temp_avg` column found in data.")

                    st.subheader("Anomaly Types (Filtered)")
                    anomaly_bar_df = filtered_df["anomaly"].value_counts().reset_index()
                    anomaly_bar_df.columns = ["anomaly_type", "count"]

                    st.plotly_chart(px.bar(
                        anomaly_bar_df,
                        x="anomaly_type", y="count",
                        labels={"anomaly_type": "Anomaly Type", "count": "Count"},
                        title="Distribution of Detected Anomalies (Filtered)"
                    ))

                    st.subheader("Average Temperature Over Time (Filtered)")
                    temp_df = filtered_df[["record_date", "temp_avg", "anomaly"]].dropna().sort_values("record_date")

                    fig = px.line(
                        temp_df,
                        x="record_date",
                        y="temp_avg",
                        title="Daily Average Temperature",
                        hover_data=["anomaly"],
                    )
                    fig.update_layout(
                        hovermode="x unified",
                        dragmode="zoom",
                        xaxis=dict(rangeslider=dict(visible=True)),
                        yaxis=dict(fixedrange=False)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

                    if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns:
                        st.subheader("Map Visualization")
                        with st.expander("View Geospatial Data"):
                            st.write("Here is a simple map of records in the selected date/anomaly range.")
                            
                            map_df = filtered_df.rename(columns={
                                "latitude": "lat",
                                "longitude": "lon"
                            })
                            map_df = map_df.dropna(subset=["lat", "lon"])
                            
                            if map_df.empty:
                                st.info("No valid latitude/longitude data found in the filtered selection.")
                            else:
                                st.map(map_df[["lat", "lon"]])

    except Exception as e:
        st.error("Failed to connect to RDS database.")
        st.text(str)
