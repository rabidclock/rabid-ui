# Use NVIDIA CUDA base for GPU support
FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Prevent Python from writing pyc files and enable real-time logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# gcc and libpam0g-dev are critical for compiling python-pam
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    tesseract-ocr \
    libtesseract-dev \
    libpam0g-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install requirements
# We install python-pam explicitly to ensure the C-bindings link correctly
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt python-pam

COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Healthcheck to ensure the 3090 bridge is responsive
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]