VOICE_CATALOG = (
    {
        "name": "James",
        "provider_voice_id": "63ff761f-c1e8-414b-b969-d1833d1c870c",
        "description": "Mature, warm British male; professional and refined.",
        "preview_path": "voice-previews/james.mp3",
    },
    {
        "name": "Sofia",
        "provider_voice_id": "79a125e8-cd45-4c13-8a67-188112f4dd22",
        "description": "Friendly, elegant female with a light European accent.",
        "preview_path": "voice-previews/sofia.mp3",
    },
    {
        "name": "Marcus",
        "provider_voice_id": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
        "description": "Confident, energetic, modern American male.",
        "preview_path": "voice-previews/marcus.mp3",
    },
    {
        "name": "Elena",
        "provider_voice_id": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        "description": "Calm, reassuring, clear American female.",
        "preview_path": "voice-previews/elena.mp3",
    },
)

VOICE_ORDER = {voice["name"]: index for index, voice in enumerate(VOICE_CATALOG)}
