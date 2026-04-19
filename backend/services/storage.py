import asyncio
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional
from ..core.config import settings

# Initialize R2 client
r2_client = boto3.client(
    's3',
    endpoint_url=settings.r2_endpoint_url,
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key,
    region_name='auto'
) if settings.r2_access_key else None

async def upload_to_r2(file_path: Path, object_key: str) -> Optional[str]:
    """Upload image to Cloudflare R2 and return public URL"""
    if not r2_client:
        return None
        
    try:
        def _upload_file():
            with open(file_path, 'rb') as file:
                r2_client.upload_fileobj(
                    file,
                    settings.r2_bucket_name,
                    object_key,
                    ExtraArgs={'ContentType': 'image/png'}
                )
        
        # Run the upload in a thread to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, _upload_file)
        
        # Return public URL
        return f"{settings.r2_public_url}/{object_key}"
    except ClientError as e:
        print(f"Error uploading to R2: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error uploading to R2: {e}")
        return None
