FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY validation-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create default directories for data
RUN mkdir -p /app/data/EPIC-files \
    /app/data/sT-files \
    /app/data/EPIC2sT-pipeline \
    /app/data/EPIC-export-validation/validation-files \
    /app/data/logs

# Copy source code
COPY validation-service/src/ /app/src/
COPY shared/ /app/shared/

# Create an entrypoint script
RUN echo '#!/bin/bash\necho "Starting EPIC-secuTrial Validation Service..."\npython /app/src/main.py' > /app/start-validation.sh && \
    chmod +x /app/start-validation.sh

# Command to run the script
CMD ["/app/start-validation.sh"]