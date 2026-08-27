from datetime import timedelta
from uuid import uuid4

from google.protobuf.json_format import ParseDict
from livekit import api

from app.config import settings
from app.schemas import LiveKitTokenRequest, LiveKitTokenResponse


class LiveKitNotConfiguredError(RuntimeError):
    pass


def create_playground_token(payload: LiveKitTokenRequest) -> LiveKitTokenResponse:
    if not all(
        (settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret)
    ):
        raise LiveKitNotConfiguredError

    room_name = payload.room_name or f"playground-{uuid4()}"
    identity = payload.participant_identity or f"tester-{uuid4()}"
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(payload.participant_name or "Meridian tester")
        .with_ttl(timedelta(minutes=10))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    if payload.participant_metadata:
        token = token.with_metadata(payload.participant_metadata)
    if payload.participant_attributes:
        token = token.with_attributes(payload.participant_attributes)
    room_config = ParseDict(payload.room_config or {}, api.RoomConfiguration())
    metadata = room_config.agents[0].metadata if room_config.agents else ""
    # The server selects exactly one worker, even for older Playground clients.
    room_config.ClearField("agents")
    room_config.agents.add(agent_name=settings.agent_name, metadata=metadata)
    token = token.with_room_config(room_config)

    return LiveKitTokenResponse(
        server_url=settings.livekit_url,
        participant_token=token.to_jwt(),
    )
