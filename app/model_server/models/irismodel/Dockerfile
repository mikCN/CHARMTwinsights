FROM python:3.10-slim

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-root

COPY iris_model ./iris_model
COPY predict.py predict ./

RUN chmod +x predict

# No ENTRYPOINT or CMD, just use the script directly
