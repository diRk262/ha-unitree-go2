"""Pure-Python LZ4 block decompressor — no C extension needed."""


def decompress_block(data: bytes, uncompressed_size: int) -> bytes:
    """Decompress an LZ4 block (raw format, no frame header)."""
    src = memoryview(data)
    dst = bytearray(uncompressed_size)
    src_pos = 0
    dst_pos = 0
    src_len = len(src)

    while src_pos < src_len:
        token = src[src_pos]
        src_pos += 1

        # Literal length
        lit_len = (token >> 4) & 0x0F
        if lit_len == 15:
            while True:
                extra = src[src_pos]
                src_pos += 1
                lit_len += extra
                if extra != 255:
                    break

        # Copy literals
        dst[dst_pos:dst_pos + lit_len] = src[src_pos:src_pos + lit_len]
        src_pos += lit_len
        dst_pos += lit_len

        if src_pos >= src_len:
            break

        # Match offset (2 bytes, little-endian)
        offset = src[src_pos] | (src[src_pos + 1] << 8)
        src_pos += 2

        # Match length
        match_len = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while True:
                extra = src[src_pos]
                src_pos += 1
                match_len += extra
                if extra != 255:
                    break

        # Copy match (byte-by-byte for overlapping copies)
        match_pos = dst_pos - offset
        for i in range(match_len):
            dst[dst_pos] = dst[match_pos]
            dst_pos += 1
            match_pos += 1

    return bytes(dst[:dst_pos])
