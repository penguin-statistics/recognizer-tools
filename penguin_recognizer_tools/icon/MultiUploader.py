import os
import logging


# MultiUploader uploads a specified file to multiple endpoints, including
# - S3
# - Upyun (via FTP)
# for S3, the following environment variables are required:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_S3_BUCKET
# - AWS_S3_REGION
# for Upyun, the following environment variables are required:
# - UPYUN_USERNAME
# - UPYUN_PASSWORD
# - UPYUN_BUCKET
# - UPYUN_ENDPOINT
class MultiUploader:
    def __init__(self, local_path: str, remote_path: str, enable_s3: bool = True, enable_upyun: bool = True):
        self.local_path = local_path
        self.remote_path = remote_path
        self.logger = logging.getLogger("MultiUploader")
        self.logger.info("uploading %s to %s", local_path, remote_path)

        if enable_s3:
            self.upload_s3()
        if enable_upyun:
            self.upload_upyun()

    def upload_s3(self):
        import boto3
        from botocore.exceptions import ClientError

        s3 = boto3.resource('s3',
                            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                            region_name=os.environ["AWS_S3_REGION"])
        bucket = s3.Bucket(os.environ["AWS_S3_BUCKET"])
        try:
            bucket.upload_file(self.local_path, self.remote_path)
            self.logger.info("uploaded to S3")
        except ClientError as e:
            self.logger.error("failed to upload to S3: %s", e)

    def upload_upyun(self):
        import ftplib
        ftp = ftplib.FTP(os.environ["UPYUN_ENDPOINT"])
        ftp.login(os.environ["UPYUN_USERNAME"], os.environ["UPYUN_PASSWORD"])

        with open(self.local_path, 'rb') as f:
            ftp.storbinary('STOR ' + self.remote_path, f)
        ftp.quit()
        self.logger.info("uploaded to Upyun")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    MultiUploader("items.zip", "newdir/newdir2/items.zip", enable_s3=False, enable_upyun=True)
