import json
from pathlib import Path

import cv2
import numpy as np


# ====== Student configuration ======
EXTRACT_FRAMES_DIR = "adaptive_extract_frames"
TARGET_FRAME_INDEX = 101
POSITION_FILE = "adaptive_position.json"
RECOVERED_FILE = "recovered_adaptive_secret.txt"
# ===================================


def checkerboard(n):
    y, x = np.indices((n, n))
    return ((x + y) % 2).astype(np.uint8)


def frame_name(frame_index):
    return f"frame_{frame_index:04d}.png"


def bits_to_bytes(bits):
    out = bytearray()
    for start in range(0, len(bits), 8):
        chunk = bits[start : start + 8]
        if len(chunk) < 8:
            break
        value = 0
        for bit in chunk:
            value = (value << 1) | int(bit)
        out.append(value)
    return bytes(out)


def main():
    position_path = Path(POSITION_FILE)
    if not position_path.exists():
        raise FileNotFoundError("adaptive_position.json not found. Run adaptive_encode.py --embed first.")

    metadata = json.loads(position_path.read_text(encoding="utf-8"))
    block_size = int(metadata["block_size"])
    bit_plane_index = int(metadata["bit_plane"])
    channel_index = int(metadata["channel"])
    secret_bit_count = int(metadata["secret_bit_count"])
    positions = metadata["positions"]

    frame_path = Path(EXTRACT_FRAMES_DIR) / frame_name(TARGET_FRAME_INDEX)
    if not frame_path.exists():
        raise FileNotFoundError(
            f"Cannot find {frame_path}. If frame numbering shifted, edit TARGET_FRAME_INDEX."
        )

    frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError(f"Cannot read frame {frame_path}")

    channel = frame[:, :, channel_index]
    bit_plane = ((channel >> bit_plane_index) & 1).astype(np.uint8)
    board = checkerboard(block_size)

    bits = []
    for pos in positions:
        y = int(pos["y"])
        x = int(pos["x"])
        valid_bits = int(pos["valid_bits"])
        block = bit_plane[y : y + block_size, x : x + block_size].copy()
        if pos.get("conjugated", False):
            block = block ^ board
        bits.extend(block.reshape(-1).tolist()[:valid_bits])

    bits = bits[:secret_bit_count]
    raw = bits_to_bytes(bits)
    if len(raw) < 4:
        raise RuntimeError("Recovered data is too short. Check TARGET_FRAME_INDEX.")

    payload_len = int.from_bytes(raw[:4], "big")
    available = max(0, len(raw) - 4)
    if payload_len <= 0 or payload_len > available:
        raise RuntimeError("Invalid payload length. Try adjusting TARGET_FRAME_INDEX.")

    payload = raw[4 : 4 + payload_len]
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Recovered bytes are not UTF-8. Try adjusting TARGET_FRAME_INDEX.") from exc

    Path(RECOVERED_FILE).write_text(text, encoding="utf-8")
    print("Recovered adaptive secret:")
    print(text)
    print(f"ADAPTIVE_BPCS_DECODE_SUCCESS {RECOVERED_FILE}")


if __name__ == "__main__":
    main()
