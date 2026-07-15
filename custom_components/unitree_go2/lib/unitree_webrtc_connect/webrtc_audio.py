import logging


class WebRTCAudioChannel:
    def __init__(self, pc, datachannel) -> None:
        self.pc = pc
        self.pc.addTransceiver("audio", direction="sendrecv")
        self.datachannel = datachannel
        self.track_callbacks = []

    async def frame_handler(self, frame):
        for callback in self.track_callbacks:
            try:
                await callback(frame)
            except Exception as e:
                logging.error(f"Error in audio callback: {e}")

    def add_track_callback(self, callback):
        if callable(callback):
            self.track_callbacks.append(callback)

    def switchAudioChannel(self, switch: bool):
        self.datachannel.switchAudioChannel(switch)
