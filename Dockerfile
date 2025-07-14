FROM python:3.11.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy wait-for-it script and make it executable
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh


# Optional: create uploads directory
RUN mkdir -p /app/uploads

# Expose port for app (e.g., FastAPI or Django)
EXPOSE 8000

# Set entrypoint
CMD ["sh", "/wait-for-it.sh"]
