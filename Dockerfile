# --- Base image ---
FROM python:3.11-slim

# --- Set working directory ---
WORKDIR /app

# --- System deps (pandas requires these) ---
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# --- Copy application ---
COPY app.py /app/app.py
COPY templates /app/templates
COPY requirements.txt /app/requirements.txt

# --- Install Python deps ---
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Expose port ---
EXPOSE 5000

# --- Run Flask app on container start ---
CMD ["python", "app.py"]
