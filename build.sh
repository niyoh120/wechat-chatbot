#!/bin/bash

set -xe

poetry export -f requirements.txt --without-hashes --output requirements.txt
# docker build -t niyoh/wechat-chatbot:latest --platform linux/amd64 . 
docker build -t niyoh/wechat-chatbot:arm64 --platform linux/arm64 .
rm -rf requirements.txt