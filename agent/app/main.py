import json
import logging
import os

import httpx
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    TurnHandlingOptions,
    function_tool,
    inference,
)

from app.api import ConciergeAPI

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("meridian.concierge")

SYSTEM_INSTRUCTIONS = """You are Meridian's voice concierge. Always speak and reply in
English, regardless of the language used by the guest or returned by a tool. Translate
Ukrainian knowledge-base answers into natural English before replying. Be warm, natural,
and concise, usually one or two sentences. Do not use Markdown, emoji, or complex
formatting because every reply is spoken aloud.

For every factual question about Meridian, the casino, restaurants, services, events, or
local recommendations, call search_meridian_faq first. The knowledge base is in Ukrainian,
so translate the guest's complete question into Ukrainian before passing it to that tool.
Never invent facts. If the tool does not find a reliable answer, call
record_unanswered_question exactly once with the guest's original wording and honestly say
that the information needs to be confirmed with a staff member. Never mention tool names,
technical fields, or match scores to the guest."""


class MeridianConcierge(Agent):
    def __init__(self, api: ConciergeAPI) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)
        self.api = api

    @function_tool()
    async def search_meridian_faq(self, context: RunContext, question: str) -> str:
        """Знайти перевірену відповідь у базі знань Meridian.

        Args:
            question: Повне питання гостя, перекладене українською для пошуку в базі знань.
        """
        try:
            result = await self.api.search_faq(question)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("FAQ lookup failed: %s", exc)
            return json.dumps({"matched": False, "reason": "service_unavailable"})
        return json.dumps(result, ensure_ascii=False)

    @function_tool()
    async def record_unanswered_question(self, context: RunContext, question: str) -> str:
        """Записати питання, коли search_meridian_faq не знайшов відповіді.

        Args:
            question: Оригінальне питання гостя, на яке база знань не відповіла.
        """
        try:
            result = await self.api.record_unanswered(question)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Could not record unanswered question: %s", exc)
            return json.dumps({"recorded": False})
        return json.dumps({"recorded": True, "id": result.get("id")})


server = AgentServer()


@server.rtc_session(agent_name=os.getenv("AGENT_NAME", "meridian-concierge"))
async def meridian_agent(ctx: agents.JobContext) -> None:
    session = AgentSession(
        stt=inference.STT(
            model=os.getenv("STT_MODEL", "deepgram/nova-3"),
            language=os.getenv("STT_LANGUAGE", "multi"),
        ),
        llm=inference.LLM(model=os.getenv("LLM_MODEL", "openai/gpt-4.1-mini")),
        tts=inference.TTS(
            model=os.getenv("TTS_MODEL", "cartesia/sonic-3"),
            voice=os.getenv(
                "TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
            ),
            language=os.getenv("TTS_LANGUAGE", "en"),
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )
    await session.start(
        room=ctx.room,
        agent=MeridianConcierge(
            ConciergeAPI(os.getenv("BACKEND_URL", "http://backend:8000"))
        ),
    )
    await session.generate_reply(
        instructions="Greet the guest briefly in English and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
