# Use official Python image
FROM python:3.12-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Environment variables (set as needed)
ENV IDOSELL_API_BASE_URL="https://vedion.pl/api/admin/v5"
# Note: IDOSELL_API_KEY and GCLOUD_CREDENTIALS_JSON should be passed at runtime

# Start FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
