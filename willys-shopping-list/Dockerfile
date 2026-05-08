ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    jq \
    curl

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages requests

COPY willys_sync.py .
COPY rootfs /
