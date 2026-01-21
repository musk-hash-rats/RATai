FROM python:3.10-slim

# Install system dependencies
# ffmpeg is required for the Music module
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# IMPORTANT: The database (database.db) is a local file.
# In Cloud Run (stateless), this file will reset on every deployment.
# We are copying the local DB if it exists, but changes made in cloud won't persist
# across restarts unless you mount a volume provided by Cloud Run (Gen 2).
# Or ideally, you should switch to Cloud SQL or a managed database.

# Command to run the bot
CMD ["python", "main.py"]
