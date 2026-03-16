FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
# copy the environment file; rename as needed
COPY .env .

COPY uv.lock .

RUN pip install --upgrade pip uv && \
    # use uv to install pinned dependencies from pyproject
    uv sync --locked

COPY . .

CMD ["uv", "run", "python", "main.py"]
