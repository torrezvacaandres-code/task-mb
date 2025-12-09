# Use Python 3.13 slim image for smaller size
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (Render will provide this via $PORT)
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import http.client, os; port = int(os.environ.get('PORT', 5000)); conn = http.client.HTTPConnection('localhost', port); conn.request('GET', '/health'); r = conn.getresponse(); exit(0 if r.status == 200 else 1)" || exit 1

# Run the application
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 60 app:app