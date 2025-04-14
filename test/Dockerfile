# Use an official Python image from DockerHub
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files into the container
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run the script
CMD ["python", "app.py"]