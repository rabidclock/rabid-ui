# sandbox/Dockerfile
FROM python:3.11-slim

# Install the "Heavy" Data Science stack
RUN pip install --no-cache-dir pandas numpy requests matplotlib scipy

# Create a non-root user for safety
RUN useradd -m sandboxuser
USER sandboxuser
WORKDIR /home/sandboxuser

# Default command (keeps container alive for exec)
CMD ["tail", "-f", "/dev/null"]
