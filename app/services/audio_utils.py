import base64
import audioop

def decode_mulaw(base64_audio: str) -> bytes:
    mulaw_bytes = base64.b64decode(base64_audio)
    pcm = audioop.ulaw2lin(mulaw_bytes, 2)
    return pcm

def encode_mulaw(pcm_audio: bytes) -> str:
    mulaw = audioop.lin2ulaw(pcm_audio, 2)
    return base64.b64encode(mulaw).decode()