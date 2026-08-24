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

SYSTEM_INSTRUCTIONS = """You are Meridian's English-only voice concierge. Conduct the
entire guest conversation in English. Never translate a guest question into another
language before calling a tool. If a guest speaks another language, politely ask them to
repeat the question in English. Tool data may be stored in Ukrainian; translate only the
verified answer into natural English before speaking. Be warm, natural, and concise,
usually one or two sentences. Do not use Markdown, emoji, or complex formatting because
every reply is spoken aloud.

For every factual question about Meridian, the casino, restaurants, services, events, or
local recommendations, call search_meridian_faq first with the guest's original complete
English wording. Never invent facts. The search tool automatically records a question when
it finds no reliable answer, using the guest's original wording. If unanswered_recorded is true, honestly say that the question
was recorded and that the information should be confirmed with a staff member. If recording
failed, do not claim that it was recorded; simply explain that the information should be
confirmed with staff. Never mention tool names, technical fields, or match scores to the
guest."""


class MeridianConcierge(Agent):
    def __init__(self, api: ConciergeAPI) -> None:
        super().__init__(instructions=SYSTEM_INSTRUCTIONS)
        self.api = api

    @function_tool()
    async def search_meridian_faq(self, context: RunContext, question: str) -> str:
        """Find a verified answer in the Meridian knowledge base.

        Args:
            question: The guest's complete original question, without translation or paraphrasing.
        """
        try:
            result = await self.api.search_and_record_unknown(question)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("FAQ lookup failed: %s", exc)
            return json.dumps(
                {
                    "matched": False,
                    "unanswered_recorded": False,
                    "reason": "service_unavailable",
                }
            )
        return json.dumps(result, ensure_ascii=False)


server = AgentServer()


async def resolve_voice_id(api: ConciergeAPI, fallback: str) -> str:
    try:
        active_voice = await api.get_active_voice()
    except (httpx.HTTPError, ValueError):
        logger.warning("Active voice unavailable; using local fallback")
        return fallback
    return active_voice["provider_voice_id"]


def build_tts(voice_id: str) -> inference.TTS:
    return inference.TTS(
        model=os.getenv("TTS_MODEL", "cartesia/sonic-3"),
        voice=voice_id,
        language=os.getenv("TTS_LANGUAGE", "en"),
    )


async def build_session(
    api: ConciergeAPI, fallback_voice_id: str
) -> AgentSession:
    voice_id = await resolve_voice_id(api, fallback_voice_id)
    return AgentSession(
        stt=inference.STT(
            model=os.getenv("STT_MODEL", "deepgram/nova-3"),
            language=os.getenv("STT_LANGUAGE", "en"),
        ),
        llm=inference.LLM(model=os.getenv("LLM_MODEL", "openai/gpt-4.1-mini")),
        tts=build_tts(voice_id),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )


@server.rtc_session(agent_name=os.getenv("AGENT_NAME", "meridian-concierge"))
async def meridian_agent(ctx: agents.JobContext) -> None:
    api = ConciergeAPI(os.getenv("BACKEND_URL", "http://backend:8000"))
    session = await build_session(
        api,
        os.getenv("TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
    )
    await session.start(
        room=ctx.room,
        agent=MeridianConcierge(api),
    )
    await session.generate_reply(
        instructions="Greet the guest briefly in English and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
