# Dockerfile for pychess-boardimage
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libcairo2 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port (change if your server uses a different port)
EXPOSE 8000

# Start the server (adjust if your entrypoint is different)
CMD ["python", "server.py"]
