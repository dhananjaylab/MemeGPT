import sys
import os
sys.path.append(os.path.abspath('.'))
from core.config import settings

print(f"R2 Account ID: {settings.r2_account_id}")
print(f"R2 Access Key ID: {settings.r2_access_key_id[:5]}...")
print(f"R2 Secret Key: {settings.r2_secret_access_key[:5]}...")
print(f"R2 Bucket: {settings.r2_bucket_name}")
print(f"R2 Endpoint: {settings.r2_endpoint_url}")
