# Use Python 3.12 as base image
FROM python:3.12-alpine

# Version and metadata labels
LABEL org.opencontainers.image.title="ocpp2mqtt"
LABEL org.opencontainers.image.description="OCPP to MQTT Gateway for EV Charging Stations"
LABEL org.opencontainers.image.version="1.0b"
LABEL org.opencontainers.image.source="https://github.com/gyzod/ocpp2mqtt"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY *.py /app
COPY requirements.txt /app

RUN pip install -r requirements.txt

# Install OCPP library from local source if present
#RUN test -d ./ocpp && pip install ./ocpp

# Command to run the Python script
CMD ["python", "/app/central_system.py"]