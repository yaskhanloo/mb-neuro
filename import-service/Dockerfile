FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY import-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create default directories for data
RUN mkdir -p /app/data/EPIC-files \
    /app/data/sT-files \
    /app/data/EPIC2sT-pipeline \
    /app/data/sT-import-validation \
    /app/data/logs

# Copy source code
COPY import-service/src/ /app/src/
COPY shared/ /app/shared/

# Create an entrypoint script
RUN echo '#!/bin/bash\necho "Starting EPIC-secuTrial Import Service..."\npython /app/src/main.py' > /app/start-import.sh && \
    chmod +x /app/start-import.sh

# Command to run the script
CMD ["/app/start-import.sh"]