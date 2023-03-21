from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
import json
import pydantic as pyd

import itchat
from itchat.content import *

import bing

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

bot = bing.new_bot()

CONVERSATION_STYLE_CHOICES = ["creative", "balanced", "precise"]


class WeChatConfig(pyd.BaseSettings):
    status_storage_dir = "itchat.pkl"

    class Config:
        env_file = ".env"
        env_prefix = "wechat_"

    
class BotConfig(pyd.BaseSettings):
    engine: str = "bing"
    conversation_style: str = "balanced"


wechat_config = WeChatConfig()
bot_config = BotConfig()


@itchat.msg_register(TEXT, isGroupChat=True)
def group_reply(msg):
    if msg.isAt:
        handle_group_msg(msg)


def handle_group_msg(msg):
    logger.debug("[WX]receive group msg: " + json.dumps(msg, ensure_ascii=False))
    group_name = msg["User"].get("NickName", None)
    if not group_name:
        return
    content: str = msg["Content"]
    content_list = content.split(" ", 1)
    context_special_list = content.split("\u2005", 1)
    sender = msg.actualNickName
    if len(context_special_list) == 2:
        content = context_special_list[1]
    elif len(content_list) == 2:
        content = content_list[1]
    if "」\n- - - - - - - - - - - - - - -" in content:
        logger.debug("[WX]reference query skipped")
        return

    def reply(content):
        msg.user.send(f"[bot]@{sender}\u2005\n{content}")

    if content.strip() == "/reset":
        asyncio.run(bot.reset())
        reply("好了，我已经为新的对话重置了我的大脑。你现在想聊些什么?")
        return

    elif content.strip().startswith("/style"):
        conversation_style = content.strip().replace("/style ", "")
        if conversation_style not in CONVERSATION_STYLE_CHOICES:
            reply(
                f"[WARN]无效的对话风格[{conversation_style}],"
                f" 有效的选项为{CONVERSATION_STYLE_CHOICES}"
            )
            return
        bot_config.conversation_style = conversation_style
        reply(f"好了，我已经设置了对话风格为[{conversation_style}].")
        return

    elif content.strip() == "/config":
        config_str = "\n".join([f"{k}:{v}" for k, v in bot_config.dict().items()])
        reply(config_str)
        return

    elif content.strip() == "/help":
        reply(
            "\n".join(
                [
                    "/config:获取对话配置",
                    f"/style:设置对话风格, 有效的选项为{CONVERSATION_STYLE_CHOICES}",
                    "/reset:重置对话",
                ]
            )
        )
        return

    async def ask():
        response = await bot.ask(
            prompt=content, conversation_style=bot_config.conversation_style
        )
        logger.debug(f"receive response:[{response}]")
        answer = response["item"]["messages"][1]["text"]
        return answer

    answer = "[WARN]没有回答"
    try:
        answer = asyncio.run(ask())
    except Exception as e:
        logger.warning(e)
        answer = f"[WARN]出错了:[{e}]"
    reply(answer)


def on_exit():
    asyncio.run(bot.close())


def main():
    itchat.auto_login(
        enableCmdQR=2, hotReload=True, statusStorageDir=wechat_config.status_storage_dir, exitCallback=on_exit
    )
    itchat.run(debug=True)


if __name__ == "__main__":
    main()
