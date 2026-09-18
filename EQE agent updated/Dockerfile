# DocuChat QA Automation — Docker support
# Build:   docker build -t docuchat-qa .
# Run:     docker run --env ENV=qa docuchat-qa
# Compose: docker-compose up

FROM python:3.12-slim

LABEL maintainer="QA Automation Team"
LABEL description="DocuChat end-to-end test runner with async Playwright"

# System dependencies required by Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc-s1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libu2f-udev \
    libvulkan1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN python -m playwright install chromium --with-deps

COPY . .

# Environment defaults (override at runtime)
ENV ENV=qa
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# Entrypoint: run all tests; exit code mirrors pytest exit code
ENTRYPOINT ["python", "-m", "pytest", "--env", "qa", "-v", "--tb=short"]
CMD []
