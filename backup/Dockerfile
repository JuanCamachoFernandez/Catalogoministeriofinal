FROM postgres:16-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 \
       python3-venv \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    google-api-python-client \
    google-auth \
    google-auth-httplib2 \
    cloudinary==1.45.0

WORKDIR /app

COPY backup/backup_drive.py /app/backup_drive.py

CMD ["python", "/app/backup_drive.py"]
