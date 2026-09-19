FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/src/app

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt && \
    rm -rf /root/.cache/pip

# App code and output/ are bind-mounted at runtime (see docker-compose.yml) —
# the image only carries the Python environment.
