import boto3
import pymysql
import csv
from datetime import datetime

# Database connection parameters
rds_host = "weather-db.c56ekmoqeysw.us-east-2.rds.amazonaws.com"
db_username = "admin"
db_password = "123456789"
db_name = "weather"

def lambda_handler(event, context):
    print("Step 1: Lambda triggered.")

    # Parse S3 event details
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    print(f"Step 2: Bucket: {bucket_name}, Key: {object_key}")

    # Connect to S3 and read CSV
    print("Step 3: Fetching S3 object...")
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    csv_lines = response['Body'].read().decode('utf-8').splitlines()
    print(f"Step 3.1: S3 File Size: {len(csv_lines)} lines")
    reader = csv.DictReader(csv_lines)
    print("Step 3.2: CSV parsed into DictReader")

    # Connect to MySQL RDS
    print("Step 4: Connecting to RDS...")
    try:
        connection = pymysql.connect(host=rds_host,
                                     user=db_username,
                                     password=db_password,
                                     database=db_name,
                                     connect_timeout=10)
        print("Step 4.1: Connected to RDS.")
    except Exception as e:
        print("ERROR: Could not connect to RDS MySQL instance.")
        print(e)
        return

    cursor = connection.cursor()
    row_count = 0
    print("Step 5: Start processing CSV rows...")

    for row in reader:
        try:
            print(f"Step 5.1: Processing row: {row}")

            date_key = 'Date'
            if '\ufeffDate' in row:
                date_key = '\ufeffDate'
            record_date = datetime.strptime(row[date_key], '%Y/%m/%d').date()
            temp_max = float(row['Maximum'])
            temp_min = float(row['Minimum'])
            temp_avg = float(row['Average'])
            departure = float(row['Departure'])
            hdd = int(row['HDD'])
            cdd = int(row['CDD'])
            new_snow = float(row['New Snow'])

            # Safe parsing for precipitation
            try:
                precip_val = float(row['Precipitation'])
                precipitation = row['Precipitation']
            except:
                precip_val = 0.0
                precipitation = '0'

            # Anomaly detection
            anomalies = []
            if temp_max > 80:
                anomalies.append("High Temperature")
            if temp_min < 10:
                anomalies.append("Low Temperature")
            if abs(departure) > 15:
                anomalies.append("Large Departure")
            if precip_val > 1.0:
                anomalies.append("Heavy Rain")
            if new_snow > 3.0:
                anomalies.append("Heavy Snow")

            anomaly_text = ', '.join(anomalies) if anomalies else "Normal"

            # Insert into database
            sql = """
                INSERT INTO weather_data 
                (record_date, temp_max, temp_min, temp_avg, departure, hdd, cdd, precipitation, new_snow, anomaly)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (record_date, temp_max, temp_min, temp_avg, departure,
                      hdd, cdd, precipitation, new_snow, anomaly_text)

            cursor.execute(sql, values)
            row_count += 1
            print("Step 5.2: Row inserted.")

        except Exception as e:
            print(f"Step 5.3: Error processing row: {row}")
            print(f"Exception: {e}")
            continue

    # Finalize DB write
    connection.commit()
    cursor.close()
    connection.close()

    print(f"Step 6: All done. Total rows inserted: {row_count}")