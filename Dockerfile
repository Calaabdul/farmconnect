FROM python:3.12

WORKDIR /app

COPY pyproject.toml .

COPY uv.lock .

RUN pip install --upgrade pip uv && \
    # use uv to install pinned dependencies from pyproject
    uv sync --locked

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
