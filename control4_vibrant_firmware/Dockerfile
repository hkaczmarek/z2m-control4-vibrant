FROM ghcr.io/home-assistant/base-python:3.14-alpine3.24

WORKDIR /app
COPY extract_firmware.py run.py /app/
COPY icons /app/icons

CMD ["python3", "-u", "/app/run.py"]
