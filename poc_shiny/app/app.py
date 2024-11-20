import os
import json
from shiny import App, Inputs, Outputs, Session, reactive, ui,render,req
from shinywidgets import output_widget, render_widget
from lonboard import Map, PolygonLayer 
import plotly.express as px
from dotenv import load_dotenv
from poc_shiny.app.gcs_get_json import get_json_from_bucket
from poc_shiny.app.load_all_data import load_country_specific_data
from poc_shiny.app.get_local_data import get_data_plot_map
import pandas as pd


load_dotenv()
bucket_name = os.getenv("GCS_BUCKET_NAME")
GCS_BUCKET_FOLDER = os.getenv("GCS_BUCKET_FOLDER")

current_path = os.path.dirname(os.path.abspath(__file__))
fpath_menu = os.path.join(current_path, "menu.json")
with open(fpath_menu, "r", encoding="utf-8-sig") as f:
    menu = json.load(f)




def get_legend_color(model,hex_color: bool = True):

    if model != "aware" :
        color_dict = {
            "Low (<10%)": "#add8e6",
            "Low - Medium (10-20%)": "#ffff99",
            "Medium - High (20-40%)": "#ffd7ba",
            "High (40-80%)": "#ff6347",
            "Extremely High (>80%)": "#ff0000",
            "Arid and Low Water Use": "#a9a9a9",
            "No Data": "#808080"
        }

    else:
        color_dict = {
            "0": "#00ff00",
            "10": "#55ff00",
            "20": "#aaff00",
            "30": "#ffff00",
            "40": "#ffaa00",
            "50": "#ff5500",
            "60": "#ff0000",
            "70": "#cc0000",
            "80": "#990000",
            "90": "#660000",
            "100": "#330000",
            "No Data": "#808080"
        }
    
    if hex_color:
        return color_dict
    else:
        # Convert hex color codes to RGB integer tuples
        try:
            return {
                k: [int(v[i:i+2], 16) for i in (1, 3, 5)]
                for k, v in color_dict.items()
            }
        except ValueError as e:
            raise ValueError(f"Invalid hex color format in color_dict: {color_dict}") from e




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
        ui.markdown("#### Water risk analysis"),    
        ui.markdown("Select the type area : "),
        ui.input_selectize("selected_analysis_type", None, choices=get_data_type()),
        ui.markdown("Select the model : "),
        ui.input_selectize("selected_model", None, choices=[]),
        ui.markdown("Select the indicator : "),
        ui.input_selectize("selected_indicator", None, choices=[]),
        ui.markdown("Select the country : "),
        ui.input_selectize("selected_country", None, choices=[]),
        ui.input_action_button("action_button", "Load Data"),
        ui.output_ui("download_button_ui"),
    )),


    ui.card(
        ui.card_header("Catergories of water stress per administrative unit 1"),
        output_widget("plot")
  
    ),

    ui.layout_columns( 



        ui.card(
            ui.card_header("Map of administrative units"),
            output_widget("map"),
            ui.card_footer(
                ui.markdown(
                    "**Note:** This highest % value define the color of the administrative unit."
                ),


            ),
        ),

        ui.card(
            ui.card_header("Data Table"),
            ui.output_data_frame("table"),
            ui.card_footer(
                ui.markdown(
                    "**Note:** Areas have been computed in the Mollweide projection. "
                    "This is a global equal-area projection that provides a balanced representation of the entire world, "
                    "making it ideal for visualizing global datasets with minimal area distortion."
                ),


            ),
            full_screen=True,
            # ui.download_button("download_df", "Download Data")

        )
    ),

    ui.layout_columns( 

        ui.card(
            ui.card_header("Methodology"),
            ui.markdown(
                """
                    The water stress analysis is focused on specific regions in 12 countries, with baseline data and advanced geospatial tools being used. Geomapped regions are overlaid with baseline water stress datasets from Aqueduct v3 and v4, along with the AWARE framework. A robust understanding of water availability and consumption pressures in each region is provided by these datasets. The integration of these layers allows for comparative insights to be highlighted, with areas of critical stress levels being identified and targeted interventions supported. All indicators have been retrieved from the initial model, allowing the most relevant indicators to be selected by the user for their analysis.
                          """
                ),
        ),
        ui.card(
            ui.card_header("Data"),
            ui.markdown(
                """
                    The water stress analysis utilizes the following data sources:

                    1. Aqueduct Baseline Water Stress Maps
                        - Version 3: [Aqueduct v3 Map](https://www.wri.org/data/aqueduct-global-maps-30-data)
                        - Version 4: [Aqueduct v4 Map](https://www.wri.org/research/aqueduct-40-updated-decision-relevant-global-water-risk-indicators)
                    2. AWARE Framework
                        - [AWARE Data Source](https://wulca-waterlca.org/aware/download-aware-factors/)
                          """
                ),
        )

    )
    )


def server(input, output, session):
    @reactive.Effect
    def update_models():
        selected_analysis_type = input.selected_analysis_type()
        if selected_analysis_type:
            models = get_list_models(selected_analysis_type)
            ui.update_select("selected_model", label=None, choices = models)
        else:
            ui.update_select("selected_model", label=None, choices = [])

    @reactive.Effect
    def update_models():
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



    df_loaded_reactive = reactive.Value()
    button_pressed = reactive.Value(False)
    


    @reactive.Calc
    def load_data():
        selected_model = input.selected_model() 
        selected_indicator = input.selected_indicator() 
        selected_country = input.selected_country() 
        selected_type = input.selected_analysis_type() 
        
        # Fetch and return data
        df, gdf, df_plot = get_data_plot_map(
            model=selected_model,
            indicator=selected_indicator,
            adm0=selected_country,
            adm1="*",
            type_area=selected_type
        )
        button_pressed.set(True)
        df_loaded_reactive.set(df)
        return df, gdf, df_plot



    @output
    @render.ui
    def download_button_ui():
        if button_pressed.get():
            return ui.download_button("download", "Download CSV")
        return None  




    @render.download(filename=f"data.csv")
    def download():
        yield load_data()[2].to_csv()



    @output
    @render.data_frame
    @reactive.event(input.action_button)
    def table():
        _,_,df = load_data()
        return render.DataGrid(df)






    @output
    @render_widget  
    def plot_no_data():
        if not button_pressed.get():
            # Create a placeholder empty DataFrame
            placeholder_df = pd.DataFrame({"x": [], "y": []})
            
            # Generate an empty placeholder plot
            fig = px.bar(
                placeholder_df,
                x="x",  # Placeholder x-axis
                y="y",  # Placeholder y-axis
                labels={"x": "Administrative Region", "y": "Percentage (%)"},
            )
            fig.update_layout(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[dict(
                    text="No Data Loaded",
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=20)
                )]
            )

            return fig


    @output
    @render_widget  
    @reactive.event(input.action_button)
    def plot():
        df, _, _ = load_data()

        # Normalize area and create percentage text
        df['normalized_area'] = df.groupby('adm1_name')['area_54009_indicator_unit'].transform(
            lambda x: round(x / x.sum() * 100)
        )
        df['normalized_area_text'] = df['normalized_area'].astype(str) + '%'

        color_map_hex = get_legend_color(input.selected_model(),hex_color = True)

        category_order = list(color_map_hex.keys())


        fig = px.bar(
            df,
            x='adm1_name',
            y='normalized_area',
            color='indicator_value_name',
            labels={'normalized_area': 'Percentage (%)', 'adm1_name': 'Administrative Region'},
            text='normalized_area_text',
            color_discrete_map=color_map_hex,
            category_orders={'indicator_value_name': category_order}
        )

        fig.update_layout(
            yaxis_title='Percentage (%)',
            xaxis_title='Administrative Region',
            barmode='stack',
            legend_title_text='Categories',
        )

        return fig
    
    @output
    @render_widget  
    @reactive.event(input.action_button)
    def map():
        _, gdf,_ = load_data()
        if gdf is None:
            return None  # Return nothing if data is not loaded
            
 
        color_map = get_legend_color(input.selected_model(),hex_color = False)
        
        list_layers = []
        for i in color_map.keys():
            gdf_current_layer = gdf.loc[gdf['indicator_value_name'] == i, :].copy()
            if gdf_current_layer.empty:
                continue
            # Drop unnecessary columns
            gdf_current_layer.reset_index(drop=True, inplace=True)
            gdf_current_layer.rename(columns={'indicator_value_name': 'Category'}, inplace=True)
            gdf_current_layer.rename(columns={'label': 'List of category'}, inplace=True)
            if 'adastra_uuid' in gdf_current_layer.columns:
                gdf_current_layer.drop(columns=['adastra_uuid'], inplace=True)
            color = color_map.get(i, [128, 128, 128])
            layer = PolygonLayer.from_geopandas(
                gdf_current_layer,
                get_line_width=1000,
                get_fill_color=color,
                get_line_color=[37, 36, 34]  # dark border color
            )
            list_layers.append(layer)
        map_widget = Map(list_layers)
        return map_widget

  


app = App(app_ui, server)



