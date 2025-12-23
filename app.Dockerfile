# Stage 1: Build stage
FROM python:3.10-alpine AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Enable community repository (usually already enabled, but ensure it)
RUN apk add --no-cache --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community

# Install build dependencies + PortAudio runtime (needed even if using py3-pyaudio)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    curl \
    libjpeg-turbo-dev \
    zlib-dev \
    libpng-dev \
    portaudio \
    py3-pyaudio  

# Copy requirements.txt and install other Python deps (skip pyaudio if listed)
COPY requirements.txt .
RUN pip install --no-cache-dir --user gradio dwani

# Stage 2: Final stage
FROM python:3.10-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only runtime dependencies
RUN apk add --no-cache \
    libjpeg-turbo \
    zlib \
    libpng \
    portaudio \  
    && rm -rf /var/cache/apk/*

# Copy Python packages from builder (including py3-pyaudio)
COPY --from=builder /root/.local /home/appuser/.local

# Update PATH for --user installs
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy the application code
COPY . .

# Create appuser and set permissions
RUN adduser -D appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser
EXPOSE 80

CMD ["python", "workshop_demo.py"]