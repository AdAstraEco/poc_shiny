from dotenv import load_dotenv
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import storage
import json

load_dotenv()

def get_json_from_bucket(bucket_name: str, bucket_suffix: str):
    # Load environment variables for OAuth 2.0 credentials
    client_id = os.getenv("client_id")
    client_secret = os.getenv("client_secret")
    refresh_token = os.getenv("refresh_token")
    quota_project_id = os.getenv("quota_project_id")

    # Set up OAuth 2.0 credentials
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        quota_project_id=quota_project_id
    )

    # Refresh token to obtain a valid access token
    credentials.refresh(Request())

    # Initialize Google Cloud Storage client with the OAuth 2.0 credentials
    client = storage.Client(credentials=credentials, project=quota_project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(bucket_suffix)

    # Download JSON content from the bucket
    json_data = blob.download_as_text()
    data = json.loads(json_data)

    return data



if __name__ == "__main__":
    bucket_name = "adastra_projects_gis"
    bucket_suffix = "poc_shiny/countries.json"

    data = get_json_from_bucket(bucket_name, bucket_suffix)
    print(data)
