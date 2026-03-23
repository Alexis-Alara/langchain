class CallSession:
    def __init__(self, stream_sid: str, tenant_id: str = None, caller_phone: str = None):
        self.stream_sid = stream_sid
        self.openai_ws = None
        self.is_model_speaking = False
        self.last_audio_time = None
        self.tenant_id = tenant_id
        self.caller_phone = caller_phone
        self.conversation_id = f"voice_{stream_sid}"
        # Stores pending function call info from Realtime API
        self.pending_function_call: dict = None