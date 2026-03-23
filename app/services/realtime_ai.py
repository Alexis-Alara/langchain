from websockets import connect
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_URL = os.getenv('OPENAI_REALTIME_URL')

async def connect_openai():
    return await connect(
        OPENAI_REALTIME_URL,
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    )