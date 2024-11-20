from pathlib import Path
import polars as pl

import pandas as pd
import os 
import json
import geopandas as gpd
from shapely import wkb
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.cloud import storage
from google.auth.transport.requests import Request
from poc_shiny.app.gcs_get_parquet import get_parquet_from_bucket


# Define the root directory for the data
ROOT_DIR = Path("/Users/regislon/Documents/no_backup/water_risk_assessment_mars/processed/parquet/exploded")
current_path = os.path.dirname(os.path.abspath(__file__))

fpath_menu = os.path.join(current_path, "menu.json")
with open(fpath_menu, "r", encoding="utf-8-sig") as f:
    menu = json.load(f)


load_dotenv()



def get_gcs_fpaths(
    model: str,
    indicator: str,
    adm0: str,
):
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket_folder = os.getenv("GCS_BUCKET_FOLDER")
    prefix = f"{bucket_folder}/model={model}/indicator={indicator}/adm0={adm0}"



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

    # List objects in the specified bucket path
    blobs = bucket.list_blobs(prefix=prefix)

    blob_names = [blob.name for blob in blobs]

    return blob_names

    






def get_local_fpaths(model: str = "*", indicator: str = "*", adm0: str = "*", adm1: str = "*", type_area: str = "*"):
    """
    Retrieve a list of parquet files based on specified filter criteria.

    Parameters:
    model (str): Model name filter (default: "*").
    indicator (str): Indicator name filter (default: "*").
    adm0 (str): Country code filter (default: "*").
    adm1 (str): Region code filter (default: "*").
    type_ (str): Type filter (default: "*").

    Returns:
    list of Path: List of file paths matching the specified criteria.
    """
    # Use Path.glob to retrieve files matching the pattern
    list_files = list(ROOT_DIR.glob(f"model={model}/indicator={indicator}/adm0={adm0}/adm1={adm1}/type={type_area}/*.parquet"))
    return list_files



def get_gcs_data(
    model: str,
    indicator: str,
    adm0: str,
    list_prefix  : list
    ):
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket_folder = os.getenv("GCS_BUCKET_FOLDER")

    list_pandas_df = []

    for prefix in list_prefix:
        
        list_elements = prefix.split("/")
        adm1 = list_elements[-3].split("=")[-1]
        


        
        df = get_parquet_from_bucket(bucket_name = bucket_name, 
                                                bucket_suffix = prefix,filter=None)
        
        df["adm1"] = adm1
        list_pandas_df.append(df)
    
    df = pd.concat(list_pandas_df)
        
    return df



    



def get_local_data(model: str = "*", indicator: str = "*", adm0: str = "*", adm1: str = "*", type_area: str = "*"):

    list_files = get_local_fpaths(model, indicator, adm0, adm1, type_area)

    list_df = []

    for file in list_files:
        # Load the parquet file using Polars
        df = pl.read_parquet(file)
        list_df.append(df)
        
    df = pl.concat(list_df)
    return df
    



def get_adm1_dict(type_area, model, indicator, adm0):
    
    for i in menu:
        if i.get("id") == type_area:
            for j in i.get("children"):
                if j.get("id") == model:
                    for x in j.get("children"):
                        if x.get("id") == indicator:
                            for y in x.get("children"):
                                if y.get("id") == adm0:
                                    dict_adm1 = {z.get("id"):z.get("name") for z in y.get("children")}
    return dict_adm1
                        


def get_indicator_dict(model):
    _dict = dict() 

    if model == "aware" :
        _dict[101] = "No Data"
        for i in range(0,101) :
            v = round(i/10)*10
            _dict[i] = str(v)
    else :
        _dict[0] = "Arid and Low Water Use"
        _dict[1] = "Low (<10%)"
        _dict[2] = "Low - Medium (10-20%)"
        _dict[3] = "Medium - High (20-40%)"
        _dict[4] = "High (40-80%)"
        _dict[5] = "Extremely High (>80%)"
        _dict[99] = "No Data"
        
    return _dict



def get_df_map(df): 
    df_pandas = df
    # df_pandas = df_pandas.sort_values(['adastra_uuid', 'area_‰'], ascending=[True, False])


    df_pandas_per_unit = df_pandas.copy()
    df_pandas_per_unit['label'] = ((df_pandas_per_unit['area_‰'] / 10).astype(str) + "% : " +  df_pandas_per_unit['indicator_value_name'])
    df_pandas_per_unit = df_pandas_per_unit.groupby(['adastra_uuid'])['label'].agg('<br>'.join).reset_index()




    df_pandas_one_per_unit = df_pandas.copy()
    # print(df_pandas_one_per_unit.shape)
    df_pandas_one_per_unit = df_pandas_one_per_unit.drop_duplicates(subset='adastra_uuid', keep='first')
    # df_pandas_one_per_unit = df_pandas_one_per_unit.loc[df_pandas_one_per_unit.groupby('adastra_uuid')['area_‰'].idxmax()]
    # print(df_pandas_one_per_unit.shape)



    df_pandas_one_per_unit = df_pandas_one_per_unit[["adastra_uuid","indicator_value_name","geometry","adm1_name","label_admin_name"]]
    df_pandas_one_per_unit = df_pandas_one_per_unit.rename(columns={"adm1_name": "Administrative unit 1 name"})
    df_pandas_one_per_unit = df_pandas_one_per_unit.rename(columns={"label_admin_name": "Municipality name"})
    df_pandas_one_per_unit = df_pandas_one_per_unit.merge(df_pandas_per_unit, on="adastra_uuid", how="left")
    # df_pandas_one_per_unit['geometry'] = df_pandas_one_per_unit['geometry'].apply(wkb.loads)
    # gdf = gpd.GeoDataFrame(df_pandas_one_per_unit, geometry='geometry',crs="EPSG:4326")


    return df_pandas_one_per_unit
    



def create_table(df,model):


    if model == "aware":
        df = df.groupby(
            ["adastra_uuid", "adm1_name", "label_admin_name", "area_54009_unit", "adm0", "indicator_value_name"],
            as_index=False
        ).agg({"area_‰": "sum"})



    # # Check for duplicates
    # duplicates = df.duplicated(subset=["adastra_uuid", "adm1_name", "label_admin_name", "area_54009_unit", "adm0", "indicator_value_name"])
    # if duplicates.any():
    #     print("Warning: There are duplicate rows in the DataFrame based on the specified columns.")
    #     print(df[duplicates]["adastra_uuid"])
    #     adastra_uuid_list = df["adastra_uuid"].unique()
    #     print("List of adastra_uuid:", adastra_uuid_list)

    _df = df.pivot(
        values="area_‰",
        index=["adastra_uuid","adm1_name","label_admin_name","area_54009_unit","adm0"],
        columns="indicator_value_name"
        )
    

    _df.reset_index(inplace=True)
    _df = _df.drop(columns=["adastra_uuid"])
    _df = _df.rename(columns={"adm1_name":"Administrative unit 1 name"})
    _df = _df.rename(columns={"label_admin_name":"Municipality name"})
    _df = _df.rename(columns={"area_54009_unit":"Area"})
    _df = _df.rename(columns={"adm0":"Country"})
    
    _df = _df.sort_values(by=["Administrative unit 1 name", "Municipality name"])


    if model != "aware":    
        column_order = [
            "Country",
            "Administrative unit 1 name",
            "Municipality name",
            "Area",
            "Arid and Low Water Use",
            "Low (<10%)",
            "Low - Medium (10-20%)",
            "Medium - High (20-40%)",
            "High (40-80%)",
            "Extremely High (>80%)",
            "No Data"
        ]

    else:
        column_order = [
            "Country",
            "Administrative unit 1 name",
            "Municipality name",
            "Area",
            "No Data",
            "0",
            "10",
            "20",
            "30",
            "40",
            "50",
            "60",
            "70",
            "80",
            "90",
            "100"
        ]
    



    _df = _df.fillna(0)

    # Reorder the columns based on the defined order
    for column in column_order:
        if column not in _df.columns:
            _df[column] = 0

    _df = _df[column_order]

    # Divide the specified columns by 10 and add a % sign
    for column in _df.columns:
        if column not in ["Country", "Administrative unit 1 name", "Municipality name", "Area"]:
            _df[column] = (_df[column] / 10).astype(str) + '%'


    return _df





def get_data_plot_map(model: str, indicator : str , adm0: str = "*", adm1: str = "*", type_area: str = "admin"):


    # Get the datafame
    # df = get_local_data(model, indicator, adm0, adm1, type_area)
    list_df_path = get_gcs_fpaths(model, indicator, adm0)
    df = get_gcs_data(model, indicator, adm0,list_df_path)

    # Get dict of indicator and adm1
    dict_indicator = get_indicator_dict(model)
    dict_adm1 = get_adm1_dict(type_area, model, indicator, adm0)
    df["adm1_name"] = df["adm1"].map(lambda x: dict_adm1.get(x, x))
    df["indicator_value_name"] = df["indicator_value"].map(lambda x: dict_indicator.get(x, x))
    df["adm0"] = adm0


    # Create table data
    df_table = create_table(df,model)
    

    # Create map data
    gdf = get_df_map(df)

    # Create plot data
    df_plot = df.groupby(["adm1_name", "indicator_value_name"], as_index=False).agg({"area_54009_indicator_unit": "sum"})

    return df_plot, gdf, df_table





if __name__ == "__main__":
#     # Example usage of get_local_data
    df,gdf,plot = get_data_plot_map(model="aqueduct_4", indicator="baseline_water_stress", adm0="BRA")
#     # ff = get_gcs_fpaths(model="aqueduct_4", indicator="seasonal_variability", adm0="BRA")
#     # gg = get_gcs_data(model="aqueduct_4", indicator="seasonal_variability", adm0="BRA", list_prefix=ff)

