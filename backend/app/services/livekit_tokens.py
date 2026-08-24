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
    if payload.room_config:
        room_config = ParseDict(payload.room_config, api.RoomConfiguration())
        token = token.with_room_config(room_config)

    return LiveKitTokenResponse(
        server_url=settings.livekit_url,
        participant_token=token.to_jwt(),
    )
