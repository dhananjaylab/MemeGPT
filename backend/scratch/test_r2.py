import boto3
import os
from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

print(f"Testing R2 with Bucket: {R2_BUCKET_NAME}")
print(f"Endpoint: {endpoint_url}")
print(f"Access Key ID: {R2_ACCESS_KEY_ID[:5]}...")

s3 = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto'
)

try:
    print("Attempting to list objects...")
    response = s3.list_objects_v2(Bucket=R2_BUCKET_NAME, MaxKeys=1)
    print("Success!")
    print(response.get('Contents', 'Bucket is empty'))
except Exception as e:
    print(f"Failed: {e}")
