# Use Python 3.11 as base image
FROM python:3.11-slim



# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install -r /app/requirements.txt

# Command to run the Python script
CMD ["python", "/app/central_system.py"]

