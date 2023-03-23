# syntax=docker/dockerfile:1

FROM python:3.9-slim as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    BING_COOKIE_FILE=/data/cookie.json \
    WECHAT_STATUS_STORAGE_DIR=/data/itchat.pkl \
    CHAT_DATA_FILE=/data/__data

WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.4.1


RUN pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.in-project true && \
    poetry install --no-dev --no-root --no-interaction --no-ansi

FROM base as final

COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY docker-entrypoint.sh .

CMD ["./docker-entrypoint.sh"]