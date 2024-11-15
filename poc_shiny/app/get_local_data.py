from pathlib import Path
import polars as pl
import os 
import json
import geopandas as gpd
from shapely import wkb

# Define the root directory for the data
ROOT_DIR = Path("/Users/regislon/Documents/no_backup/water_risk_assessment_mars/processed/parquet/exploded")
current_path = os.path.dirname(os.path.abspath(__file__))

fpath_menu = os.path.join(current_path, "menu.json")
with open(fpath_menu, "r", encoding="utf-8-sig") as f:
    menu = json.load(f)



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
        _dict[2] = "Medium - High (20-40%)"
        _dict[3] = "Low - Medium (10-20%)"
        _dict[4] = "High (40-80%)"
        _dict[5] = "Extremely High (>80%)"
        _dict[99] = "No Data"
        
    return _dict



def get_df_map(df): 
    df_pandas = df.to_pandas()


    df_pandas_per_unit = df_pandas.copy()
    df_pandas_per_unit['label'] = (df_pandas_per_unit['indicator_value_name'] + ' (' +  (df_pandas_per_unit['area_‰'] / 10).astype(str) + "%)")
    df_pandas_per_unit = df_pandas_per_unit.groupby('adastra_uuid')['label'].agg(', '.join).reset_index()


    df_pandas_one_per_unit = df_pandas.copy()
    print(df_pandas_one_per_unit.columns)
    df_pandas_one_per_unit = df_pandas_one_per_unit.loc[df_pandas_one_per_unit.groupby('adastra_uuid')['area_‰'].idxmax()]



    df_pandas_one_per_unit = df_pandas_one_per_unit[["adastra_uuid","indicator_value_name","geometry"]]
    df_pandas_one_per_unit = df_pandas_one_per_unit.merge(df_pandas_per_unit, on="adastra_uuid", how="left")
    df_pandas_one_per_unit['geometry'] = df_pandas_one_per_unit['geometry'].apply(wkb.loads)
    gdf = gpd.GeoDataFrame(df_pandas_one_per_unit, geometry='geometry',crs="EPSG:4326")


    return gdf
    





def get_local_data_plot_map(model: str, indicator : str , adm0: str = "*", adm1: str = "*", type_area: str = "*"):



    df = get_local_data(model, indicator, adm0, adm1, type_area)

    dict_indicator = get_indicator_dict(model)
    dict_adm1 = get_adm1_dict(type_area, model, indicator, adm0)


    df = df.with_columns(pl.col("adm1").map_elements(lambda x: dict_adm1.get(x, x), return_dtype=pl.Utf8).alias("adm1_name"))
    df = df.with_columns(pl.col("indicator_value").map_elements(lambda x: dict_indicator.get(x, x), return_dtype=pl.Utf8).alias("indicator_value_name"))



    gdf = get_df_map(df)
    
    if indicator and  not indicator == "*":
        df_grouped = df.group_by(["indicator","model","adm0","adm1_name","type","indicator_value_name"]).agg(pl.sum("area_54009_indicator_unit"))
    
    df_grouped = df_grouped.select(["adm1_name","indicator_value_name","area_54009_indicator_unit"])


    return df_grouped.to_pandas(), gdf





# if __name__ == "__main__":
#     # Example usage of get_local_data
#     df,gdf = get_local_data_plot_map(model="aqueduct_4", indicator="baseline_water_water_stress", adm0="CIV", adm1="*", type_area="farms")
#     print(df,gdf)
