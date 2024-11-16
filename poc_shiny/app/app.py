import os
import json
from shiny import App, Inputs, Outputs, Session, reactive, ui
from shinywidgets import output_widget, render_widget 
from lonboard import Map, PolygonLayer 
import plotly.express as px
from dotenv import load_dotenv
from poc_shiny.app.gcs_get_json import get_json_from_bucket
from poc_shiny.app.load_all_data import load_country_specific_data
from poc_shiny.app.get_local_data import get_data_plot_map


load_dotenv()
bucket_name = os.getenv("GCS_BUCKET_NAME")
GCS_BUCKET_FOLDER = os.getenv("GCS_BUCKET_FOLDER")

current_path = os.path.dirname(os.path.abspath(__file__))
fpath_menu = os.path.join(current_path, "menu.json")
with open(fpath_menu, "r", encoding="utf-8-sig") as f:
    menu = json.load(f)


def get_data_type():
    # list_type = dict()
    # for i in menu:
    #     list_type[i.get("id")] = i.get("name")
    # return list_type
    return {"admin": "Administrative Boundaries"}



def get_list_models(selected_analysis_type : str):
    if selected_analysis_type :
        for i in menu:
            if i.get("id") == selected_analysis_type:
                dict_ = {}
                for j in i.get("children"):
                    dict_[j.get("id")] = j.get("name")
        return dict_
    else : 
        return {}




def get_indicators(selected_analysis_type, selected_model):
    if selected_analysis_type and selected_model:
        for i in menu:
            if i.get("id") == selected_analysis_type:
                for j in i.get("children"):
                    if j.get("id") == selected_model:
                        dict_ = {}
                        for x in j.get("children"):
                            dict_[x.get("id")] = x.get("name")
        return dict_
    else :
        return {}
                        
     




def get_countries(selected_analysis_type, selected_model, selected_indicator):
    dict_ = {}
    if selected_analysis_type and selected_model and selected_indicator:
        for i in menu:
            if i.get("id") == selected_analysis_type:
                for j in i.get("children"):
                    if j.get("id") == selected_model:
                        for x in j.get("children"):
                            if x.get("id") == selected_indicator:
                                for y in x.get("children"):
                                    dict_[y.get("id")] = y.get("name")
        return dict_
    else :
        return {}

    




app_ui = ui.page_sidebar(
    ui.sidebar((
        ui.input_selectize("selected_analysis_type", None, choices=get_data_type()),
        ui.input_selectize("selected_model", None, choices=[]),
        ui.input_selectize("selected_indicator", None, choices=[]),
        ui.input_selectize("selected_country", None, choices=[]),
        ui.input_action_button("action_button", "Load Data") 
    )),
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
        selected_analysis_type = input.selected_analysis_type()
        if selected_analysis_type:
            models = get_list_models(selected_analysis_type)
            ui.update_select("selected_model", label=None, choices = models)
        else:
            ui.update_select("selected_model", label=None, choices = [])

    @reactive.Effect
    def update_indicators():
        selected_analysis_type = input.selected_analysis_type()
        selected_model = input.selected_model()
        if selected_model:
            indicators = get_indicators(selected_analysis_type,selected_model)
            ui.update_select("selected_indicator", label=None, choices = indicators)
        else:
            ui.update_select("selected_indicator", label=None, choices = [])



    @reactive.Effect
    def update_countries():
        selected_analysis_type = input.selected_analysis_type()
        selected_model = input.selected_model()
        selected_indicator = input.selected_indicator()
        if selected_analysis_type:
            countries = get_countries(selected_analysis_type, selected_model, selected_indicator)
            ui.update_select("selected_country", label=None, choices = countries)
        else:
            ui.update_select("selected_country", label=None, choices = [])


    @reactive.Calc
    def load_data():
        selected_model = input.selected_model()
        selected_indicator = input.selected_indicator()
        selected_country = input.selected_country()
        selected_type = input.selected_analysis_type()

        
        df,gdf = get_data_plot_map(model=selected_model, indicator=selected_indicator, adm0=selected_country, adm1="*", type_area=selected_type)
        return df,gdf


    @output
    @render_widget  
    @reactive.event(input.action_button)
    def plot():
        df, _ = load_data()

        # Normalize area and create percentage text
        df['normalized_area'] = df.groupby('adm1_name')['area_54009_indicator_unit'].transform(
            lambda x: round(x / x.sum() * 100)
        )
        df['normalized_area_text'] = df['normalized_area'].astype(str) + '%'

        # Convert RGB color_map to HEX color codes
        color_map_hex = {
            "Low (<10%)": "#add8e6",
            "Medium - High (20-40%)": "#ffd7ba",
            "Low - Medium (10-20%)": "#ffff99",
            "High (40-80%)": "#ff6347",
            "Extremely High (>80%)": "#ff0000",
            "Arid and Low Water Use": "#a9a9a9",
            "No Data": "#808080"
        }

        # Create the bar plot with custom colors
        fig = px.bar(
            df,
            x='adm1_name',
            y='normalized_area',
            color='indicator_value_name',
            labels={'normalized_area': 'Percentage (%)', 'adm1_name': 'Administrative Region'},
            title='Categories of Indicators by Administrative Region',
            text='normalized_area_text',
            color_discrete_map=color_map_hex  # Apply the custom colors
        )

        # Update layout for better visualization
        fig.update_layout(
            yaxis_title='Percentage (%)',
            xaxis_title='Administrative Region',
            barmode='stack',
            legend_title_text='Indicator Category',
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
            "Low (<10%)" :  [173, 216, 230],  # light blue
            "Medium - High (20-40%)": [255, 223, 186],  # light orange
            "Low - Medium (10-20%)": [255, 255, 153],   # light yellow
            "High (40-80%)": [255, 99, 71],             # tomato
            "Extremely High (>80%)": [255, 0, 0],       # red
            "Arid and Low Water Use": [169, 169, 169],  # dark grey
            "No Data": [128, 128, 128]                  # grey
        }

        
        list_layers = []
        for i in color_map.keys():
            gdf_current_layer = gdf.loc[gdf['indicator_value_name'] == i, :].copy()
            if gdf_current_layer.empty:
                continue
            # Drop unnecessary columns
            gdf_current_layer.reset_index(drop=True, inplace=True)
            if 'adastra_uuid' in gdf_current_layer.columns:
                gdf_current_layer.drop(columns=['adastra_uuid'], inplace=True)
            color = color_map.get(i, [128, 128, 128])
            layer = PolygonLayer.from_geopandas(
                gdf_current_layer,
                get_fill_color=color,
                get_line_color=[0, 0, 0, 255]
            )
            list_layers.append(layer)
        map_widget = Map(list_layers)
        return map_widget

  


app = App(app_ui, server)



