from pathlib import Path


PREVIEW_DIR = Path(__file__).parents[1] / "app" / "static" / "voice-previews"


def test_all_four_real_voice_previews_are_committed() -> None:
    for name in ("james", "sofia", "marcus", "elena"):
        preview = PREVIEW_DIR / f"{name}.mp3"
        assert preview.exists(), name
        assert preview.stat().st_size > 1_000, name
        header = preview.read_bytes()[:3]
        assert header == b"ID3" or header[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
