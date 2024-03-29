import boto3

from app.config.config import S3_KEY, S3_SECRET

s3 = boto3.client(
   "s3",
   aws_access_key_id=S3_KEY,
   aws_secret_access_key=S3_SECRET
)
