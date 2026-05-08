ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    jq

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages requests

COPY run.sh /
RUN chmod a+x /run.sh

COPY willys_sync.py .

CMD [ "/run.sh" ]
