FROM python:3.11-slim

WORKDIR /ralph

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    git \
    jq \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    anthropic \
    ollama \
    playwright \
    pytest \
    pytest-playwright

# Install Playwright browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Create workspace directory
RUN mkdir -p /workspace

# Set bash as default shell
SHELL ["/bin/bash", "-c"]

# Keep container running
CMD ["tail", "-f", "/dev/null"]
