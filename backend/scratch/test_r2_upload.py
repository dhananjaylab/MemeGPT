import boto3
import os
import io
from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto'
)

try:
    print(f"Testing simple PutObject to {R2_BUCKET_NAME}...")
    s3.put_object(
        Bucket=R2_BUCKET_NAME,
        Key="test_upload.txt",
        Body=b"Hello R2!",
        ContentType="text/plain"
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
