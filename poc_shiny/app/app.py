import os

from shiny import App, Inputs, Outputs, Session, reactive, ui
from shinywidgets import output_widget, render_widget 
from lonboard import Map, PolygonLayer 
import plotly.express as px
from dotenv import load_dotenv
from poc_shiny.app.gcs_get_json import get_json_from_bucket
from poc_shiny.app.load_all_data import load_country_specific_data



load_dotenv()
bucket_name = os.getenv("GCS_BUCKET_NAME")
GCS_BUCKET_FOLDER = os.getenv("GCS_BUCKET_FOLDER")



def get_indicators():
    return get_json_from_bucket(bucket_name, f"{GCS_BUCKET_FOLDER}/indicators.json")

    

def get_countries(selected_analysis_type : str):
    countries = get_json_from_bucket(bucket_name, f"{GCS_BUCKET_FOLDER}/countries.json")
    if selected_analysis_type == "Farms":
        list_countries = countries.get("farms")
    else : 
        list_countries = countries.get("admin")
    return list_countries  
    


def get_list_models():
    return list(get_indicators().keys())


def get_list_indicators(model : str):
    return list(get_indicators().get(model).keys())


def get_analysis_type():
    # return ["Farms", "Administrative units"]
    return  ["Administrative units"]




app_ui = ui.page_sidebar(
    ui.sidebar((
        ui.input_selectize("selected_analysis_type", None, choices=get_analysis_type()),
        ui.input_selectize("selected_model", None, choices=get_list_models()),
        ui.input_selectize("selected_indicator", None, choices=[]),
        ui.input_selectize("selected_country", None, choices=[])),
        ui.input_action_button("action_button", "Load Data") 
    ),
    ui.card(
        output_widget("plot")
    ),

    ui.card(
        output_widget("map")
    ),


    title="Poc Shiny"
    )


def server(input, output, session):
    @reactive.Effect
    def update_indicators():
        selected_model = input.selected_model()
        if selected_model:
            indicators = get_list_indicators(selected_model)
            ui.update_select("selected_indicator", label=None, choices = indicators)
        else:
            ui.update_select("selected_indicator", label=None, choices = [])

    @reactive.Effect
    def update_countries():
        selected_analysis_type = input.selected_analysis_type()
        if selected_analysis_type:
            countries = get_countries(selected_analysis_type)
            ui.update_select("selected_country", label=None, choices = countries)
        else:
            ui.update_select("selected_country", label=None, choices = [])


    @reactive.Calc
    def load_data():
        print("Loading data")
        selected_model = input.selected_model()
        selected_indicator = input.selected_indicator()
        selected_country = input.selected_country()
        
        # Ensure that all inputs are provided before loading data
        if selected_model and selected_indicator and selected_country:
            grouped_df, gdf = load_country_specific_data(
                selected_model, selected_indicator, selected_country, data_type="admin"
            )
            print("Data loaded")
            return grouped_df, gdf
        
        else:
            print("Data not loaded")
            return None, None


    @output
    @render_widget  
    @reactive.event(input.action_button)
    def plot():
        df_plot, _ = load_data()
        if df_plot is None:
            return None  # Return nothing if data is not loaded

        color_map = {
            0: "red",
            1: "orange",
            2: "yellow",
            3: "green",
            4: "blue",
            5: "purple",
            99: "grey"
        }
        
        df_plot["color"] = df_plot["value"].map(color_map)
        
        fig = px.pie(
            df_plot,
            names="value",
            values="total_area_ha",
            title="Distribution of the Indicator",
            color_discrete_map=color_map,
            hole=0.3
        )
        return fig
    
    @output
    @render_widget  
    @reactive.event(input.action_button)
    def map():
        _, gdf = load_data()
        if gdf is None:
            return None  # Return nothing if data is not loaded

        color_map = {
            0: [255, 0, 0],       # red
            1: [255, 165, 0],     # orange
            2: [255, 255, 0],     # yellow
            3: [0, 128, 0],       # green
            4: [0, 0, 255],       # blue
            5: [128, 0, 128],     # purple
            99: [128, 128, 128]   # grey
        }
        list_layers = []
        for i in color_map.keys():
            gdf_current_layer = gdf.loc[gdf['indicator_value'] == i, :].copy()
            if gdf_current_layer.empty:
                continue
            # Drop unnecessary columns
            if 'adastra_uuid' in gdf_current_layer.columns:
                gdf_current_layer.drop(columns=['adastra_uuid'], inplace=True)
            color = color_map.get(i, [128, 128, 128])
            layer = PolygonLayer.from_geopandas(
                gdf_current_layer,
                get_fill_color=color,
                get_line_color=[0, 100, 100, 150]
            )
            list_layers.append(layer)
        map_widget = Map(list_layers)
        return map_widget

  


app = App(app_ui, server)



