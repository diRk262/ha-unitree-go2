"""LiDAR voxel decoder — decompresses lz4 voxel data to point cloud."""
import numpy as np

from .lz4_decode import decompress_block


def _bits_to_points(buf, origin, resolution=0.05):
    buf = np.frombuffer(bytearray(buf), dtype=np.uint8)
    nonzero_indices = np.nonzero(buf)[0]

    if len(nonzero_indices) == 0:
        return np.empty((0, 3), dtype=np.float64)

    byte_values = buf[nonzero_indices]
    bits = np.unpackbits(byte_values).reshape(-1, 8)

    z = nonzero_indices // 0x800
    n_slice = nonzero_indices % 0x800
    y = n_slice // 0x10
    x_base = (n_slice % 0x10) * 8

    z_expanded = np.repeat(z, 8)
    y_expanded = np.repeat(y, 8)
    x = np.repeat(x_base, 8) + np.tile(np.arange(8), len(nonzero_indices))

    mask = bits.ravel() == 1
    points = np.column_stack((x[mask], y_expanded[mask], z_expanded[mask]))

    return points * resolution + origin


class NativeLidarDecoder:
    def decode(self, compressed_data, metadata):
        try:
            decompressed = decompress_block(
                compressed_data, metadata["src_size"]
            )
            points = _bits_to_points(
                decompressed, metadata["origin"], metadata.get("resolution", 0.05)
            )
            return {"points": points}
        except Exception:
            return {}


class UnifiedLidarDecoder:
    def __init__(self, decoder_type="native"):
        self.decoder = NativeLidarDecoder()
        self.decoder_name = "NativeDecoder"

    def decode(self, compressed_data, metadata):
        return self.decoder.decode(compressed_data, metadata)

    def get_decoder_name(self):
        return self.decoder_name
