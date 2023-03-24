import typing as t
import json
import asyncio
import copy

import structlog
from EdgeGPT import Chatbot, ChatHub, Conversation
import pydantic as pyd


logger = structlog.get_logger(__name__)


class Config(pyd.BaseSettings):
    cookie_file: str = "./cookie.json"

    class Config:
        env_file = ".env"
        env_prefix = "bing_"

class Conversation:
    """
    Conversation API
    """

    def __init__(self, cookiePath: str = "", cookies: dict | None = None) -> None:
        self.struct: dict = {
            "conversationId": None,
            "clientId": None,
            "conversationSignature": None,
            "result": {"value": "Success", "message": None},
        }
        self.session = httpx.Client()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            },
        )
        if cookies is not None:
            cookie_file = cookies
        else:
            f = (
                open(cookiePath, encoding="utf8").read()
                if cookiePath
                else open(os.environ.get("COOKIE_FILE"), encoding="utf-8").read()
            )
            cookie_file = json.loads(f)
        for cookie in cookie_file:
            self.session.cookies.set(cookie["name"], cookie["value"])
        url = "https://edgeservices.bing.com/edgesvc/turing/conversation/create"
        # Send GET request
        response = self.session.get(
            url,
            timeout=30,
            headers=HEADERS_INIT_CONVER,
        )
        if response.status_code != 200:
            print(f"Status code: {response.status_code}")
            print(response.text)
            raise Exception("Authentication failed")
        try:
            self.struct = response.json()
            if self.struct["result"]["value"] == "UnauthorizedRequest":
                raise NotAllowedToAccess(self.struct["result"]["message"])
        except (json.decoder.JSONDecodeError, NotAllowedToAccess) as exc:
            raise Exception(
                "Authentication failed. You have not been accepted into the beta.",
            ) from exc

class Bot:
    _cookies = None

    def __init__(
        self, bot_id: str, style: str = "balanced", context=None, **kwargs
    ) -> None:
        self.bot_id = bot_id
        self._style = style
        self._bot = Chatbot(cookies=self._cookies)
        self._conversation = Conversation(cookies=self._cookies)
        self._chat_hub = ChatHub(self._conversation)
        self._count = 0

    def ask(self, prompt: str) -> str:
        # response = asyncio.run(self._bot.ask(prompt, conversation_style=self._style))  # type: ignore
        self._count += 1
        logger.info(f"[bot:{self.bot_id}]receive response:[{response}]")
        answers = []
        # return "\n".join(answers)
        """
        Ask a question to the bot
        """

        async def ask(
            prompt: str,
            conversation_style: CONVERSATION_STYLE_TYPE = None,
        ) -> dict:
            """
            Ask a question to the bot
            """
            async for final, response in self._chat_hub.ask_stream(
                prompt=prompt,
                conversation_style=conversation_style,
            ):
                if final:
                    await self._chat_hub.wss.close()
                    return response
            await self._chat_hub.wss.close()
            return None

        response = asyncio.run(ask(prompt, conversation_style=self._style))  # type: ignore
        if response is None:
            return "No response"
        for msg in response["item"]["messages"]:
            if msg["author"] != "user":
                answers.append(msg["text"])
        if len(answers) == 0:
            return "Empty response"
        return "\n".join(answers)

    def reset(self):
        self._count = 0
        return asyncio.run(self._bot.reset())

    def close(self):
        return asyncio.run(self._bot.close())

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style):
        self._style = style

    @property
    def engine(self) -> str:
        return "bing"

    def info(self):
        return dict(
            bot_id=self.bot_id, engine=self.engine, style=self.style, count=self._count
        )

    def serialize(self):
        context = copy.deepcopy(self._bot.chat_hub.request.struct)
        info = self.info()
        return dict(info=info, context=context)

    @classmethod
    def deserialize(cls, data: t.Dict[str, t.Any]) -> "Bot":
        info = data["info"]
        context = data["context"]
        return cls(bot_id=info["bot_id"], style=info["style"], context=context)


config = Config()
with open(config.cookie_file, "r") as f:
    Bot._cookies = json.load(f)
