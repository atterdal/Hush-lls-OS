ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    jq \
    curl \
    chromium \
    chromium-chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages \
    requests \
    selenium

COPY willys_sync.py .
COPY rootfs /
