FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directories
RUN mkdir -p /app/data/EPIC-files \
    /app/data/sT-files \
    /app/data/EPIC2sT-pipeline \
    /app/data/EPIC-export-validation/validation-files \
    /app/data/logs

# Copy source code
COPY . /app/

# Create entrypoint script
RUN echo '#!/bin/bash\necho "Starting EPIC-secuTrial Pipeline..."\nif [ "$1" = "validate" ]; then\n  python /app/validation-service/src/main.py\nelif [ "$1" = "import" ]; then\n  python /app/import-service/src/main.py\nelse\n  echo "Usage: docker run epic-pipeline [validate|import]"\nfi' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["validate"]