FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Robocorp RCC
RUN curl -o rcc https://downloads.robocorp.com/rcc/releases/latest/linux64/rcc && \
    chmod +x rcc && \
    mv rcc /usr/local/bin/

# Copy requirements file
COPY orchestrator/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY orchestrator/ .
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
