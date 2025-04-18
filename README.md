# DS4300_WeatherGuard

**WeatherGuard** is a serverless weather anomaly detection and visualization pipeline built using AWS and Streamlit. It allows users to upload CSV files containing historical weather data, detects anomalies using Lambda, and displays the cleaned results in a modern web interface.

---

## Features

- Upload weather data CSVs via a web interface
- Automated anomaly detection (e.g., high/low temperature, heavy rain/snow, large temperature departure)
- Cleaned and labeled data stored in an AWS RDS MySQL instance
- Dynamic Streamlit dashboard with filters, charts, and download support
- Fully serverless architecture using S3, Lambda, RDS, and EC2-hosted Streamlit

---

## Architecture Overview

1. **Frontend Upload**  
   - Users upload CSV via Streamlit app running on EC2.
   - The file is stored in an S3 bucket (`boston-weather-raw`).

2. **Data Processing with Lambda**  
   - Triggered automatically when a new CSV appears in S3.
   - Cleans and parses the file, detects anomalies, and inserts processed rows into `weather_data` table in RDS.

3. **Data Analysis Dashboard**  
   - Reads from the RDS database.
   - Allows filtering by date and anomaly type.
   - Displays summary metrics, line charts, bar charts, and downloadable CSVs.

---

## Sample Anomalies Detected

- `High Temperature` if `temp_max > 80°F`
- `Low Temperature` if `temp_min < 10°F`
- `Heavy Rain` if `precipitation > 1 inch`
- `Heavy Snow` if `new_snow > 3 inches`
- `Large Departure` if `|departure| > 15°F`

---

## File Structure

| File            | Description                                        |
|-----------------|----------------------------------------------------|
| `app.py`        | Streamlit frontend with upload + analysis interface |
| `Lambda.py`     | Lambda function triggered by S3 upload             |
| `weather.png`   | Image shown in dashboard header (optional)         |
---

## Setup Instructions

> Prerequisites: AWS account, IAM roles configured, RDS MySQL instance, S3 buckets created

1. **Deploy Lambda Function**
   - Use `Lambda.py` as the source code.
   - Connect to the correct S3 bucket trigger.
   - Ensure `pymysql` is included as a Lambda layer if needed.
   - Allow VPC access if your RDS is private.

2. **Set Up MySQL Table**
   ```sql
   CREATE TABLE weather_data (
       id INT AUTO_INCREMENT PRIMARY KEY,
       record_date DATE,
       temp_max FLOAT,
       temp_min FLOAT,
       temp_avg FLOAT,
       departure FLOAT,
       hdd INT,
       cdd INT,
       precipitation VARCHAR(10),
       new_snow FLOAT,
       anomaly VARCHAR(255)
   );
