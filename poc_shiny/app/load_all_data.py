
from pathlib import Path
from typing import Optional
import json
import polars as pl
import pandas as pd
import os 
from dotenv import load_dotenv
from poc_shiny.app.gcs_get_parquet import get_parquet_from_bucket
from poc_shiny.app.gcs_get_json import get_json_from_bucket


load_dotenv()


def load_country_specific_data(
    model: str, 
    indicator: str, 
    country: str,
    data_type : str = "admin"
) -> pd.DataFrame :
    

    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket_folder = os.getenv("GCS_BUCKET_FOLDER")

    # Load the config file
    bucket_suffix = f"{bucket_folder}/indicators.json"
    dict_indicators = get_json_from_bucket(bucket_name, bucket_suffix)

    # Retrieve the specific indicator value, with checks for missing keys
    model_data = dict_indicators.get(model)
    if not model_data:
        raise ValueError(f"Model '{model}' not found in indicators configuration.")
    
    indicator_data = model_data.get(indicator)
    if not indicator_data:
        raise ValueError(f"Indicator '{indicator}' not found in model '{model}' configuration.")

    current_indicator = indicator_data.get('indicator')
    if not current_indicator:
        raise ValueError(f"Indicator name for '{indicator}' in model '{model}' is missing.")
    


    # Load the indicators data
    filter = {"indicator_name": current_indicator,"country": country}
    df_indicators = get_parquet_from_bucket(bucket_name = bucket_name, 
                                            bucket_suffix = f"{bucket_folder}/df_{data_type}_indicators.parquet", 
                                            filter = filter)
    
    
    # Replace values and cast type
    df_indicators['indicator_value'] = df_indicators['indicator_value'].replace(['-9999', '-', '-1'], 99).astype('uint8')

    # Load the geometry data
    filter = {"country": country}
    gdf = get_parquet_from_bucket(bucket_name = bucket_name, 
                                            bucket_suffix = f"{bucket_folder}/{data_type}.parquet", 
                                            filter = filter)
    
    

    # Prepare the data for the plot   
    admin_areas = gdf[['area_ha','adastra_uuid']]
    df_indicators_with_area = pd.merge(df_indicators, admin_areas, on='adastra_uuid', how='left')
    df_indicators_with_area["adjusted_area"] = df_indicators_with_area["area_ha"] * df_indicators_with_area["ratio_per_1000"] / 1000
    grouped_df = df_indicators_with_area.groupby("indicator_value", as_index=False)["adjusted_area"].sum()
    df_plot = grouped_df.rename(columns={"indicator_value": "value", "adjusted_area": "total_area_ha"})

    

    # prepare the data for the map
    grouped_df = df_indicators_with_area.groupby(["indicator_value","adastra_uuid"], as_index=False)["adjusted_area"].sum()
    sum_per_uuid = df_indicators_with_area.groupby("adastra_uuid", as_index=False)["adjusted_area"].sum()
    grouped_df = grouped_df.merge(sum_per_uuid, on='adastra_uuid', how='left')
    grouped_df["ratio"] = grouped_df["adjusted_area_x"] / grouped_df["adjusted_area_y"]
    grouped_df["ratio"] = grouped_df["ratio"].round(2)
    grouped_df["label"] = grouped_df["indicator_value"].astype(str) + " (" + grouped_df["ratio"].astype(str) + ")"
    grouped_df = grouped_df.groupby("adastra_uuid").agg({
        "label": lambda x: ", ".join(x),
        "indicator_value": "max"
    }).reset_index()
    grouped_df = grouped_df[['adastra_uuid', 'label', 'indicator_value']]
    gdf = gdf[['adastra_uuid','geom']]
    gdf = gdf.merge(grouped_df, on='adastra_uuid', how='left')
    gdf = gdf.set_crs(4326)


    return df_plot,gdf

    





