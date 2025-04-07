# Use Python 3.10 as base image
FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install -r requirements.txt

# Install OCPP library from local source if present
#RUN test -d ./ocpp && pip install ./ocpp

# Command to run the Python script
CMD ["python", "/app/central_system.py"]

