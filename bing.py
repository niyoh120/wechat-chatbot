import json
from EdgeGPT import Chatbot
import pydantic as pyd


class Config(pyd.BaseSettings):
    cookie_file: str = "./cookie.json"

    class Config:
        env_file = ".env"
        env_prefix = "bing_"


config = Config()


def new_bot():
    with open(config.cookie_file, "r") as f:
        cookies = json.load(f)
    return Chatbot(cookies=cookies)
