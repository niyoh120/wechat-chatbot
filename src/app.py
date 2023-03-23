import json

import structlog
import pydantic as pyd
import itchat
import itchat.content
from dotenv import load_dotenv

import bing

load_dotenv()

bing.init()

logger = structlog.get_logger(__name__)

CONVERSATION_STYLE_CHOICES = ["creative", "balanced", "precise"]


class WeChatConfig(pyd.BaseSettings):
    status_storage_dir = "itchat.pkl"

    class Config:
        env_file = ".env"
        env_prefix = "wechat_"


wechat_config = WeChatConfig()


def handle_msg(msg, content, reply_prefix=""):
    if "」\n- - - - - - - - - - - - - - -" in content:
        logger.info("[WX]reference query skipped")
        return

    bot = bing.Bot.get_or_create(msg.user.userName)

    def reply(reply_content):
        msg.user.send(f"{reply_prefix}{reply_content}")

    if content.strip() == "/reset":
        bot.reset()
        reply("好了，我已经为新的对话重置了我的大脑。你现在想聊些什么?")
        return

    elif content.strip().startswith("/style"):
        style = content.strip().replace("/style ", "")
        if style not in CONVERSATION_STYLE_CHOICES:
            reply(f"[WARN]无效的对话风格[{style}], 有效的选项为{CONVERSATION_STYLE_CHOICES}")
            return
        bot.style = style
        reply(f"好了，我已经设置了对话风格为[{style}].")
        return

    elif content.strip() == "/info":
        config_str = "\n".join([f"{k}:{v}" for k, v in bot.info().items()])
        reply(config_str)
        return

    elif content.strip() == "/help":
        reply(
            "\n".join(
                [
                    "/info:获取机器人信息",
                    f"/style:设置对话风格, 有效的选项为{CONVERSATION_STYLE_CHOICES}",
                    "/reset:重置对话",
                ]
            )
        )
        return

    answer = "[WARN]没有回答"
    try:
        answer = bot.ask(content)
    except Exception as e:
        logger.warning(e)
        answer = f"[WARN]出错了:[{e}]"
    reply(answer)


def handle_group_msg(msg):
    content: str = msg.content
    content_list = content.split(" ", 1)
    context_special_list = content.split("\u2005", 1)
    if len(context_special_list) == 2:
        content = context_special_list[1]
    elif len(content_list) == 2:
        content = content_list[1]
    sender = msg.actualNickName
    reply_prefix = f"[bot]@{sender}\u2005\n\n"
    handle_msg(msg, content, reply_prefix=reply_prefix)


@itchat.msg_register(itchat.content.TEXT, isGroupChat=True)
def group_reply(msg):
    if msg.isAt:
        logger.info("[WX]receive group msg: " + json.dumps(msg, ensure_ascii=False))
        handle_group_msg(msg)


@itchat.msg_register(itchat.content.TEXT, isFriendChat=True)
def single_reply(msg):
    logger.info("[WX]receive msg: " + json.dumps(msg, ensure_ascii=False))
    handle_msg(msg, msg.content)


def on_exit():
    bing.Bot.close_all()


def main():
    itchat.auto_login(
        enableCmdQR=2,  # type: ignore
        hotReload=True,
        statusStorageDir=wechat_config.status_storage_dir,
        exitCallback=on_exit,
    )
    itchat.run(debug=True)


if __name__ == "__main__":
    main()
