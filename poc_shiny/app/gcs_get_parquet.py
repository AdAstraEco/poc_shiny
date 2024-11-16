from dotenv import load_dotenv
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import storage
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import gcsfs
from shapely import wkb
import geopandas as gpd

load_dotenv()

def get_parquet_from_bucket(bucket_name: str, bucket_suffix: str, filter: dict):
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

    # Construct the GCS file path and initialize gcsfs with OAuth credentials
    gcs_path = f"gs://{bucket_name}/{bucket_suffix}"
    fs = gcsfs.GCSFileSystem(token=credentials)

    # Load the Parquet file and filter rows using pyarrow
    dataset = ds.dataset(gcs_path, filesystem=fs, format="parquet")

    if filter : 

        # Create the filter expression based on the provided dictionary
        filter_expression = [(ds.field(column) == value) for column, value in filter.items()]
        
        # Combine filter expressions if there are any, otherwise set to None
        combined_filter = None
        if filter_expression:
            combined_filter = filter_expression[0]
            for expr in filter_expression[1:]:
                combined_filter &= expr

        # Read the filtered data
        table = dataset.to_table(filter=combined_filter)
    else :
        table = dataset.to_table()

    # Convert to pandas DataFrame for easier handling
    data = table.to_pandas()

    if "geometry" in data.columns:
        data["geometry"] = data["geometry"].apply(lambda x: wkb.loads(x) if isinstance(x, bytes) else x)
        data = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326") 

    return data


# if __name__ == "__main__":
#     bucket_name = "adastra_projects_gis"
#     bucket_suffix = "poc_shiny/admin.parquet"

#     filter = {"country": "Brazil"}

#     data = get_parquet_from_bucket(bucket_name, bucket_suffix, filter)
#     print(data)
