# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV POETRY_VERSION=1.5.1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PORT=8080

# Install GDAL and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock if they exist, and install dependencies
COPY pyproject.toml poetry.lock* ./
RUN poetry install

# Copy the rest of the application code
COPY poc_shiny/ poc_shiny/

# Set PYTHONPATH to make `poc_shiny` available as a module
ENV PYTHONPATH=/app

# Expose the port that Shiny will run on
EXPOSE 8080

# Copy .env file if needed by your app
COPY .env .env

# Start Shiny app, dynamically reading the PORT environment variable
CMD ["sh", "-c", "shiny run poc_shiny.app.app --host=0.0.0.0 --port=${PORT}"]