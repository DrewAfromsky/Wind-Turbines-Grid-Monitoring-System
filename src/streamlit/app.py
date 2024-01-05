import streamlit as st
import subprocess
from pathlib import Path
from zipfile import ZipFile
import os

from markdown_text import APP_USAGE, APP_FUNCTIONALITY


PROJECT_DIR = Path(__file__).parent.parent.parent.absolute()
# METRICS_DATA_PATH = PROJECT_DIR / "metrics_data"
METRICS_DATA_PATH = PROJECT_DIR / "/data/metrics_data"


def run_wind_turbines():
    """Run the grid monitor and wind turbine in two separate subprocess sequentially."""    
    path_to_main = PROJECT_DIR / "src" / "main.py"
    subprocess.run(["python3", str(path_to_main), "run-wind-turbine"], capture_output=True)


def get_metrics_from_turbines():
    """Retrieves the metrics for each turbine from the metrics_data 
    folder and places them inside streamlit the text field
    """

    for t in range(1, 6):
        with open(METRICS_DATA_PATH / f"turbine_{t}.txt", "r") as f:
            st.text(f"Metrics for turbine {t}:\n {f.read()}")
            st.text("--------------------------------------------------")


def generate_zip_file_for_metrics():
    """Zips the turbine metrics files from the wind turbines"""
    with ZipFile(METRICS_DATA_PATH / 'metrics.zip', 'w') as myzip:
        for t in range(1,6):
            myzip.write(f'{METRICS_DATA_PATH}/turbine_{t}.txt', f'turbine_{t}.txt')


def create_GUI():
    """Creates the GUI for the streamlit app"""

    st.title("Wind Turbine Monitoring System")
    st.markdown(APP_FUNCTIONALITY)
    st.markdown(APP_USAGE)

    if st.button(
        "Run Wind Turbines", 
        help="Runs a Typer app on the backend to create wind turbines and push their metrics to a grid monitoring app endpoint"):
        try:
            run_wind_turbines()
        except Exception as e:
            st.error("Could not run the wind turbines. Please try again. Here was the error:\n")
            st.error(e)
            # TODO disable the button if the wind turbines are already running

    if st.button(
        "Display Metrics", 
        help="Displays the metrics from the wind turbines in the browser\n this can be pressed many times to update the metrics displayed"):
        metrics_data_contents = os.listdir(METRICS_DATA_PATH)
        if len(metrics_data_contents) != 0:
            try:
                get_metrics_from_turbines()  # Metrics are only displayed once per click (e.g. on-demand)
            except Exception as e:
                st.error("There was an error retrieving the metrics. Please try again. Here was the error:\n")
                st.error(e)
        else:
            st.error("No metrics have been recorded. Please run the wind turbines first.")

    if st.button(
        "Zip Turbine Metrics", 
        help="Zips the turbine metrics files from the wind turbines and provides user with a download button for direct download"): # \
        
        metrics_data_contents = os.listdir(METRICS_DATA_PATH)
        
        if len(metrics_data_contents) != 0:
            generate_zip_file_for_metrics()
            st.success("Metrics persisted as zip file successfully!")

            st.text("Download the metrics zip file to your local machine, here:\n")
            with open(METRICS_DATA_PATH / "metrics.zip", "rb") as f:
                st.download_button(
                    label="Download Wind Turbine Metrics",
                    data=f,
                    file_name="metrics.zip",
                    mime="application/zip",
                    key="metrics_download",
                )
            #         # try:
            #         #     st.success("Successfully downloaded metrics zip file!")
            #         # except Exception as e:
            #         #     st.error("There was an error downloading the metrics zip file. Please try again. Here was the error:\n")
            #         #     st.error(e)
        else:
            st.error("No metrics have been recorded. Please run the wind turbines first.")
    
    # if st.button(
    #     "Shutdown the App", 
    #     help="Shuts down the wind turbines and all running processes"):
    #     try:
    #         # subprocess.run(["pkill", "-f", "main.py"])
    #         subprocess.run(["docker compose down --volumes", "&&", "docker image rm smartgridmonitor-wt smartgridmonitor-gm smartgridmonitor-test"])
    #         st.success("Successfully shut down the wind turbines!")
    #     except Exception as e:
    #         st.error("There was an error shutting down the wind turbines. Please try again. Here was the error:\n")
    #         st.error(e)  # [Errno 2] No such file or directory: 'docker compose down --volumes'

if __name__ == "__main__":
    create_GUI()