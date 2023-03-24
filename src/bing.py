import typing as t
import json
import asyncio
import copy

import structlog
import httpx
from EdgeGPT import ChatHub
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

    def __init__(self, context) -> None:
        self.struct = context


class Client(ChatHub):
    def __init__(self, context: t.Dict[str, t.Any]) -> None:
        conv = Conversation(context)
        super().__init__(conv)  # type: ignore
        self.request.invocation_id = context["invocation_id"]


HEADERS_INIT_CONVER = {
    "authority": "edgeservices.bing.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Microsoft Edge";v="110"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"110.0.1587.69"',
    "sec-ch-ua-full-version-list": (
        '"Chromium";v="110.0.5481.192", "Not A(Brand";v="24.0.0.0", "Microsoft'
        ' Edge";v="110.0.1587.69"'
    ),
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"15.0.0"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.69"
    ),
    "x-edge-shopping-flag": "1",
    "x-forwarded-for": "1.1.1.1",
}


def create_conversation_context(cookies) -> t.Dict[str, t.Any]:
    session = httpx.Client()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
                " like Gecko) Chrome/108.0.0.0 Safari/537.36"
            ),
        },
    )
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"])
    url = "https://edgeservices.bing.com/edgesvc/turing/conversation/create"
    # Send GET request
    response = session.get(
        url,
        timeout=30,
        headers=HEADERS_INIT_CONVER,
    )
    if response.status_code != 200:
        logger.warn(f"Status code:{response.status_code}, message:{response.text}")
        raise RuntimeError("Authentication failed")
    try:
        context = response.json()
        if context["result"]["value"] == "UnauthorizedRequest":
            raise RuntimeError(context["result"]["message"])
    except (json.decoder.JSONDecodeError, RuntimeError) as exc:
        raise RuntimeError(
            "Authentication failed. You have not been accepted into the beta.",
        ) from exc
    session.close()
    context["invocation_id"] = 0
    return context


class Bot:
    _cookies = None

    def __init__(
        self, bot_id: str, style: str = "balanced", context=None, count=0, **kwargs
    ) -> None:
        self.bot_id = bot_id
        self._style = style
        if context is None:
            self._context = create_conversation_context(self._cookies)
        else:
            self._context = context
        self._client = Client(self._context)
        self._count = count

    def ask(self, prompt: str) -> str:
        """
        Ask a question to the bot
        """

        async def ask(
            prompt: str,
            conversation_style: t.Optional[str] = None,
        ) -> t.Optional[t.Dict[str, t.Any]]:
            """
            Ask a question to the bot
            """
            response = None
            async for final, response in self._client.ask_stream(
                prompt=prompt,
                conversation_style=conversation_style,  # type: ignore
            ):
                if final:
                    break
            await self._client.close()
            return response  # type: ignore

        self._count += 1
        answers = []
        response = asyncio.run(ask(prompt, conversation_style=self._style))  # type: ignore
        if response is None:
            return "No response"
        logger.info(f"[bot:{self.bot_id}]receive response:[{response}]")
        for msg in response["item"]["messages"]:
            if msg["author"] != "user":
                answers.append(msg["text"])
        if len(answers) == 0:
            return "Empty response"
        return "\n".join(answers)

    def reset(self):
        self._count = 0
        asyncio.run(self._client.close())
        self._context = create_conversation_context(self._cookies)
        self._client = Client(self._context)

    def close(self):
        asyncio.run(self._client.close())

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
        assert self._context is not None
        context = copy.deepcopy(dict(**self._context))
        context["invocation_id"] = self._client.request.invocation_id
        info = self.info()
        return dict(info=info, context=context)

    @classmethod
    def deserialize(cls, data: t.Dict[str, t.Any]) -> "Bot":
        info = data["info"]
        context = data["context"]
        return cls(
            bot_id=info["bot_id"],
            style=info["style"],
            count=info["count"],
            context=context,
        )


config = Config()
with open(config.cookie_file, "r") as f:
    Bot._cookies = json.load(f)
