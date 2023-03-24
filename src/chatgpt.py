import json
import typing as t

import structlog

# from langchain.agents import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.schema import messages_from_dict, messages_to_dict

logger = structlog.get_logger(__name__)


class Bot:
    def __init__(
        self, bot_id: str, model_name="gpt-3.5-turbo", memory=None, **kwargs
    ) -> None:
        self.bot_id = bot_id
        self._count = 0
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        if memory is not None:
            self.memory.chat_memory.messages = memory
        self.llm = ChatOpenAI(model_name=model_name, temperature=0)
        self.agent_chain = initialize_agent(
            [],
            self.llm,
            agent="chat-conversational-react-description",
            memory=self.memory,
            verbose=True,
        )

    def ask(self, prompt: str) -> str:
        if not self.can_continue:
            return "对不起, 我的大脑容量不够了, 请重置我的记忆后重试."
        return self.agent_chain.run(input=prompt)

    def reset(self):
        self._count = 0
        self.memory.clear()

    def close(self):
        pass

    @property
    def can_continue(self) -> bool:
        # return len(self.memory.buffer) < 1024
        return True

    @property
    def engine(self) -> str:
        return self.llm.model_name

    def info(self):
        return dict(bot_id=self.bot_id, engine=self.engine, count=self._count)

    def serialize(self) -> t.Dict:
        info = self.info()
        memory = messages_to_dict(self.memory.chat_memory.messages)
        print(memory)
        return dict(info=info, memory=memory)

    @classmethod
    def deserialize(cls, data: t.Dict[str, t.Any]) -> "Bot":
        info = data["info"]
        memory = messages_from_dict(data["memory"])
        print(data)
        return cls(bot_id=info["bot_id"], model_name=info["engine"], memory=memory)
