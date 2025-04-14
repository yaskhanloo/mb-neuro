FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY import-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the notebook
COPY import-service/import_EPIC2sT_20250303.ipynb .

# Create default directories for data
RUN mkdir -p /app/data/EPIC-files \
    /app/data/sT-files \
    /app/data/EPIC2sT-pipeline \
    /app/data/EPIC-export-validation/validation-files \
    /app/data/sT-import-validation

# Create startup script to launch Jupyter
RUN echo '#!/bin/bash\necho "Starting EPIC-secuTrial Import Service..."\njupyter notebook --ip=0.0.0.0 --port=8889 --no-browser --allow-root' > /app/start-jupyter.sh && \
    chmod +x /app/start-jupyter.sh

# Expose Jupyter port
EXPOSE 8889

# Command to run Jupyter
CMD ["/app/start-jupyter.sh"]