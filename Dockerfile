# Create a layer from the Python 3.10 image
FROM python:3.10 as grid-monitor-app

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Define the network ports that this container will listen on at runtime.
EXPOSE 8787

# Set the current working directory to /code.
WORKDIR /code

# Copy the file with the requirements to the /code directory.
COPY ./requirements.txt /code/requirements.txt

# Install the package dependencies defined in the requirements file.
# The --no-cache-dir option tells pip to not save the downloaded packages locally.
# The --upgrade option tells pip to upgrade the packages if they are already installed.
RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the files inside of source code directory "src" inside the /code directory.
COPY ./src /code/src/

# Run the grid monitor application
CMD ["python3", "/code/src/main.py", "run-grid-monitor"]

# Run the wind turbine application; this image is built on top of the grid-monitor-app image
FROM grid-monitor-app as wind-turbine-app

# Container needs to listen to Streamlit’s (default) port 8501
EXPOSE 8501

# Configure the container that will run as an executable. 
# It contains the entire streamlit run command for the app, avoiding having to call it from the command line
ENTRYPOINT ["streamlit", "run", "/code/src/streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Create a new target called test that will run the test suite
FROM grid-monitor-app as test
CMD ["python3", "-m", "pytest", "-vv", "/code/src/tests/test_main.py", "--disable-warnings"]
