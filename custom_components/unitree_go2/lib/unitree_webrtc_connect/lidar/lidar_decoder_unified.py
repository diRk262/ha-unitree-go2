"""Stub LiDAR decoder — full decoding not needed for HA sensor integration."""


class _StubDecoder:
    def decode(self, compressed_data, metadata):
        return {}


class UnifiedLidarDecoder:
    def __init__(self, decoder_type="libvoxel"):
        self.decoder = _StubDecoder()
        self.decoder_name = "StubDecoder"

    def decode(self, compressed_data, metadata):
        return self.decoder.decode(compressed_data, metadata)

    def get_decoder_name(self):
        return self.decoder_name
