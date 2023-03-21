# syntax=docker/dockerfile:1

FROM python:3.9-alpine

RUN mkdir -p /data

WORKDIR /app
ENV BING_COOKIE_FILE /data/cookie.json
ENV WECHAT_STATUS_STORAGE_DIR /data/itchat.pkl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "./app.py"]