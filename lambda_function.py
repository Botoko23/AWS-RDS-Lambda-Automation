import os

import boto3
import pymysql
from botocore.exceptions import NoCredentialsError

import gspread
import pandas as pd
from gspread import Spreadsheet
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials

query_mapping = {
    "select_all": "SELECT * FROM test;",
    "select_where": "SELECT * FROM test WHERE QUANTITYORDERED > 35;"
}

def get_workbook(wb_id:str) -> Spreadsheet:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    wb = client.open_by_key(wb_id)
    return wb

def lambda_handler(event: dict, context):
    db_host = os.getenv("DB_HOST")  # Replace with your RDS endpoint
    db_port = os.getenv("DB_PORT")  # Default MySQL port
    db_user = os.getenv("DB_USER")  # The IAM database user you created in the RDS instance
    db_name = os.getenv("DB_NAME")  # Replace with your actual database name
    db_pass = os.getenv("DB_PASS")
    wb_id = os.getenv("WB_ID")

    task = event.get('task', 'no task')
    query = query_mapping.get(task)
    update_sheet = event.get('sheet', 'Test')

    try:
        # Connect to MySQL using the IAM authentication token
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,  # Use the IAM token as the password
            database=db_name,
            port=int(db_port),
            ssl_ca='us-east-1-bundle.pem',  # Path to Amazon RDS SSL certificate
            cursorclass=pymysql.cursors.DictCursor
        )

        result = None

        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            print("Result:", result)
        
        df = pd.DataFrame(result)
        wb = get_workbook(wb_id=wb_id)
        test_sheet = wb.worksheet(update_sheet)
        set_with_dataframe(test_sheet, df, row=1, 
                           col=1, include_index=False, include_column_header=True)

        # Return the result as a response
        return {
            "statusCode": 200,
            "body": "Successful"
        }

    except NoCredentialsError:
        print('failed connection')
        return {
            "statusCode": 403,
            "body": "IAM Authentication failed: No valid credentials"
        }

    except Exception as e:
        print(str(e))
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }

    finally:
        if conn:
            conn.close()

