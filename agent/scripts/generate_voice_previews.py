import argparse
import asyncio
import os
from pathlib import Path

import lameenc
from dotenv import load_dotenv
from livekit.agents import inference, utils


VOICE_IDS = {
    "james": "63ff761f-c1e8-414b-b969-d1833d1c870c",
    "sofia": "79a125e8-cd45-4c13-8a67-188112f4dd22",
    "marcus": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
    "elena": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
}
PREVIEW_TEXT = "Welcome to The Meridian. It is my pleasure to assist you today."


def require_livekit_credentials() -> None:
    required = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    if any(not os.getenv(name) for name in required):
        raise RuntimeError("LiveKit credentials are required")


async def synthesize_mp3(voice_id: str) -> bytes:
    tts = inference.TTS(
        model="cartesia/sonic-3",
        voice=voice_id,
        language="en",
    )
    encoder = None
    encoded = bytearray()

    try:
        async with tts.synthesize(PREVIEW_TEXT) as stream:
            async for event in stream:
                frame = event.frame
                if encoder is None:
                    encoder = lameenc.Encoder()
                    encoder.set_bit_rate(128)
                    encoder.set_in_sample_rate(frame.sample_rate)
                    encoder.set_channels(frame.num_channels)
                    encoder.set_quality(2)
                encoded.extend(encoder.encode(frame.data.tobytes()))
    finally:
        await tts.aclose()

    if encoder is None:
        raise RuntimeError("LiveKit returned no audio")
    encoded.extend(encoder.flush())
    if len(encoded) <= 1_000:
        raise RuntimeError("Generated preview audio is unexpectedly short")
    return bytes(encoded)


async def generate_previews(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, voice_id in VOICE_IDS.items():
        audio = await synthesize_mp3(voice_id)
        target = output_dir / f"{name}.mp3"
        temporary = target.with_suffix(".mp3.tmp")
        temporary.write_bytes(audio)
        temporary.replace(target)
        print(f"{target.name}: {len(audio)} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Meridian voice previews")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    load_dotenv()
    require_livekit_credentials()
    async def run() -> None:
        async with utils.http_context.open():
            await generate_previews(args.output_dir.resolve())

    asyncio.run(run())


if __name__ == "__main__":
    main()
