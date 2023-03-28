from dotenv import load_dotenv

load_dotenv()

import json
import datetime

import structlog
import pydantic as pyd
import itchat
import itchat.content


import data
import bing
import chatgpt


logger = structlog.get_logger(__name__)

CONVERSATION_STYLE_CHOICES = ["creative", "balanced", "precise"]
bot_type_map = {
    "bing": bing.Bot,
    "gpt-3.5-turbo": chatgpt.Bot,
}
CHAT_ENGINE_CHOICES = list(bot_type_map.keys())


class WeChatConfig(pyd.BaseSettings):
    status_storage_dir = "itchat.pkl"

    class Config:
        env_file = ".env"
        env_prefix = "wechat_"


wechat_config = WeChatConfig()


def get_or_create_bot(bot_id: str, engine="bing"):
    assert engine in bot_type_map

    if bot_id in data.g_dict["bots"]:
        engine = data.g_dict["bots"][bot_id]["info"]["engine"]
        return bot_type_map[engine].deserialize(data.g_dict["bots"][bot_id])
    return bot_type_map[engine](bot_id)


def switch_bot(bot, engine):
    assert engine in bot_type_map

    if bot.engine == engine:
        bot.reset()
        return bot
    bot.close()
    bot = bot_type_map[engine](bot.bot_id)
    return bot


def save_bot(bot):
    data.g_dict["bots"][bot.bot_id] = bot.serialize()


def handle_msg(msg, content, reply_prefix=""):
    current_timestamp = int(datetime.datetime.now().timestamp())

    # 5分钟前的信息不处理, 一般是重启后重复收到的消息
    if current_timestamp - msg.createTime > 5 * 60:
        logger.info(f"[WX]ignore too old message, {msg}")
        return

    if "」\n- - - - - - - - - - - - - - -" in content:
        logger.info("[WX]reference query skipped")
        return

    def reply(bot, reply_content):
        save_bot(bot)
        bot.close()
        msg.user.send(f"{reply_prefix}{reply_content}")

    bot = get_or_create_bot(msg.user.userName)

    if content.startswith("/"):
        if content.strip() == "/reset":
            bot.reset()
            reply(bot, "好了，我已经为新的对话重置了我的大脑。你现在想聊些什么?")
            return

        elif content.strip().startswith("/style"):
            if bot.engine != "bing":
                reply(bot, f"{bot.engine}引擎不支持更改对话风格")
                return
            engine = content.strip().replace("/style ", "")
            if engine not in CONVERSATION_STYLE_CHOICES:
                reply(
                    bot, f"[WARN]无效的对话风格[{engine}], 有效的选项为{CONVERSATION_STYLE_CHOICES}."
                )
                return
            bot.style = engine
            reply(bot, f"好了，我已经设置了对话风格为[{engine}].")
            return

        elif content.strip() == "/info":
            config_str = "\n".join([f"{k}:{v}" for k, v in bot.info().items()])
            reply(bot, config_str)
            return

        elif content.strip() == "/help":
            reply(
                bot,
                "\n".join(
                    [
                        "/info:获取机器人信息.",
                        (
                            "/style:设置对话风格, 只有bing引擎支持,"
                            f" 有效的选项为{CONVERSATION_STYLE_CHOICES}."
                        ),
                        f"/engine:设置对话引擎, 有效的选项为{CHAT_ENGINE_CHOICES}",
                        "/reset:重置对话.",
                    ]
                ),
            )
            return

        elif content.strip().startswith("/engine"):
            engine = content.strip().replace("/engine ", "")
            if engine not in bot_type_map:
                reply(
                    bot, f"[WARN]无效的对话引擎[{engine}], 有效的选项为{list(bot_type_map.keys())}."
                )
                return
            bot = switch_bot(bot, engine)
            reply(bot, f"好了，我已经设置了对话引擎为[{engine}]. 注意, 我已经忘记了之前的对话.")
            return

        reply(bot, f"[WARN]无效的对话命令[{content}].输入/help查询有效的命令.")
        return

    answer = "[WARN]没有回答"
    try:
        answer = bot.ask(content)
    except Exception as e:
        logger.warning(e)
        answer = f"[WARN]出错了:[{e}]"
    reply(bot, answer)


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
    pass


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
