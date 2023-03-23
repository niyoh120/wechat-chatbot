import json
import asyncio

import structlog
from EdgeGPT import Chatbot
import pydantic as pyd

import data

logger = structlog.get_logger(__name__)

class Config(pyd.BaseSettings):
    cookie_file: str = "./cookie.json"

    class Config:
        env_file = ".env"
        env_prefix = "bing_"


class Bot:
    _all_bots = {}
    _cookies = None

    def __init__(self, bot_id: str, style: str, **kwargs) -> None:
        self._bot_id = bot_id
        self._style = style
        self._bot = Chatbot(cookies=self._cookies)
        self._all_bots[bot_id] = self
        self._count = 0

    def ask(self, prompt: str) -> str:
        response = asyncio.run(self._bot.ask(prompt, conversation_style=self._style))  # type: ignore
        self._count += 1
        logger.info(f"[bot:{self._bot_id}]receive response:[{response}]")
        answers = []
        for msg in response["item"]["messages"]:
            if msg["author"] != "user":
                answers.append(msg["text"])
        return "\n".join(answers)

    def reset(self):
        self._count = 0
        return asyncio.run(self._bot.reset())

    def close(self):
        return asyncio.run(self._bot.close())

    @classmethod
    def close_all(cls):
        for bot in cls._all_bots.values():
            bot.close()

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style):
        self._style = style
        self.save()

    @property
    def engine(self) -> str:
        return "bing"

    @classmethod
    def get_or_create(cls, bot_id):
        if bot_id in cls._all_bots:
            return cls._all_bots[bot_id]
        if bot_id in data.g_dict["bots"]:
            bot_data = data.g_dict["bots"][bot_id]
            return cls(**bot_data)
        return Bot(bot_id, "balanced")

    def info(self):
        return dict(
            bot_id=self._bot_id, engine=self.engine, style=self.style, count=self._count
        )

    def save(self):
        data.g_dict["bots"][self._bot_id] = self.info()


def init():
    data.init()
    if "bots" not in data.g_dict:
        data.g_dict["bots"] = {}
    if Bot._cookies is None:
        config = Config()
        with open(config.cookie_file, "r") as f:
            Bot._cookies = json.load(f)
