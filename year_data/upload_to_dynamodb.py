import csv
import boto3
from decimal import Decimal

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')  # Replace 'eu-west-2' with your table's region
table = dynamodb.Table('BTCUSDT_1_yeardata')

# Function to convert and clean data before uploading
def clean_data(row):
    cleaned_row = {}
    for key, value in row.items():
        if key:  # Only add non-empty keys
            if key in ['Open', 'High', 'Low', 'Close', 'Volume']:
                cleaned_row[key] = Decimal(str(value))
            else:
                cleaned_row[key] = value
    return cleaned_row

# Read the CSV file and upload each row to DynamoDB
with open('/home/ec2-user/machdtrading/year_data/BTCUSDT_data.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        cleaned_row = clean_data(row)
        print(cleaned_row)  # Print the row being uploaded
        table.put_item(Item=cleaned_row)
