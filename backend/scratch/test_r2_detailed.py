import boto3
import os
from dotenv import load_dotenv
from botocore.config import Config

load_dotenv()

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

print(f"Testing R2 with Bucket: {R2_BUCKET_NAME}")
print(f"Endpoint: {endpoint_url}")

def test_config(name, region, signature_version=None):
    print(f"\n--- Testing config: {name} (region={region}, sig={signature_version}) ---")
    
    config = Config()
    if signature_version:
        config = Config(signature_version=signature_version)
        
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name=region,
        config=config
    )
    
    try:
        print("Attempting to list objects...")
        response = s3.list_objects_v2(Bucket=R2_BUCKET_NAME, MaxKeys=1)
        print("Success!")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

# Try common configurations
test_config("Standard R2 (auto)", "auto")
test_config("Standard R2 (us-east-1)", "us-east-1")
test_config("R2 with s3v4 signature", "auto", signature_version='s3v4')
