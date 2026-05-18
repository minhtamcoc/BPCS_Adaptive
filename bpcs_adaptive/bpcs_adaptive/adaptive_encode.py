import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


# ====== Student configuration ======
FRAMES_DIR = "frames"
AUDIO_FILE = "audio.mp3"
OUTPUT_VIDEO = "adaptive_output.avi"
TARGET_FRAME_INDEX = 100
SECRET_DATA = "Adaptive BPCS conjugation"
FPS = 30

POSITION_FILE = "adaptive_position.json"
THRESHOLD_REPORT = "threshold_report.txt"
MESSAGE_BLOCKS_FILE = "message_blocks.json"

BLOCK_SIZE = 8
BIT_PLANE = 0
CHANNEL = 0  # BGR channel: 0=B, 1=G, 2=R

BASE_ALPHA = 0.30
ADAPTIVE_MARGIN = 0.05
MAX_FINAL_THRESHOLD = 0.45
# ===================================


def text_to_bits(text):
    payload = text.encode("utf-8")
    length_header = len(payload).to_bytes(4, "big")
    data = length_header + payload
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def checkerboard(n):
    y, x = np.indices((n, n))
    return ((x + y) % 2).astype(np.uint8)


def block_complexity(block):
    horizontal = np.sum(block[:, :-1] != block[:, 1:])
    vertical = np.sum(block[:-1, :] != block[1:, :])
    max_transitions = 2 * block.shape[0] * (block.shape[0] - 1)
    return float(horizontal + vertical) / float(max_transitions)


def bits_to_blocks(bits, block_size):
    block_bits = block_size * block_size
    blocks = []
    for start in range(0, len(bits), block_bits):
        chunk = bits[start : start + block_bits]
        valid_bits = len(chunk)
        if len(chunk) < block_bits:
            chunk = chunk + [0] * (block_bits - len(chunk))
        block = np.array(chunk, dtype=np.uint8).reshape(block_size, block_size)
        blocks.append((block, valid_bits))
    return blocks


def frame_name(frame_index):
    return f"frame_{frame_index:04d}.png"


def load_target_bit_plane():
    frame_path = Path(FRAMES_DIR) / frame_name(TARGET_FRAME_INDEX)
    if not frame_path.exists():
        raise FileNotFoundError(
            f"Cannot find {frame_path}. Run: ffmpeg -i video.mp4 frames/frame_%04d.png"
        )

    frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError(f"Cannot read frame {frame_path}")

    channel = frame[:, :, CHANNEL].copy()
    bit_plane = ((channel >> BIT_PLANE) & 1).astype(np.uint8)
    return frame, channel, bit_plane, frame_path


def iter_block_coords(height, width):
    for y in range(0, height - height % BLOCK_SIZE, BLOCK_SIZE):
        for x in range(0, width - width % BLOCK_SIZE, BLOCK_SIZE):
            yield y, x


def prepare_payload_blocks():
    secret_bits = text_to_bits(SECRET_DATA)
    raw_blocks = bits_to_blocks(secret_bits, BLOCK_SIZE)
    board = checkerboard(BLOCK_SIZE)
    prepared = []

    for index, (block, valid_bits) in enumerate(raw_blocks):
        alpha_before = block_complexity(block)
        conjugated = alpha_before < BASE_ALPHA
        stored_block = block ^ board if conjugated else block
        alpha_after = block_complexity(stored_block)
        prepared.append(
            {
                "index": index,
                "block": stored_block,
                "valid_bits": valid_bits,
                "alpha_before": alpha_before,
                "alpha_after": alpha_after,
                "conjugated": conjugated,
            }
        )

    return secret_bits, prepared


def compute_cover_complexities(bit_plane):
    values = []
    height, width = bit_plane.shape
    for y, x in iter_block_coords(height, width):
        block = bit_plane[y : y + BLOCK_SIZE, x : x + BLOCK_SIZE]
        values.append(block_complexity(block))
    return values


def compute_adaptive_threshold(bit_plane, payload_blocks):
    cover_alphas = compute_cover_complexities(bit_plane)
    payload_alphas = [entry["alpha_after"] for entry in payload_blocks]
    min_alpha_prime = min(payload_alphas)
    max_alpha_prime = max(payload_alphas)

    # The final threshold must keep data blocks noise-like but still leave
    # enough complex cover blocks for embedding.
    final_threshold = max(BASE_ALPHA, min_alpha_prime - ADAPTIVE_MARGIN)
    final_threshold = min(final_threshold, MAX_FINAL_THRESHOLD)

    usable_cover_blocks = sum(1 for alpha in cover_alphas if alpha >= final_threshold)
    return {
        "base_alpha": BASE_ALPHA,
        "adaptive_margin": ADAPTIVE_MARGIN,
        "min_alpha_prime": min_alpha_prime,
        "max_alpha_prime": max_alpha_prime,
        "final_threshold": final_threshold,
        "payload_blocks": len(payload_blocks),
        "conjugated_blocks": sum(1 for entry in payload_blocks if entry["conjugated"]),
        "cover_blocks": len(cover_alphas),
        "usable_cover_blocks": usable_cover_blocks,
    }


def write_reports(threshold_info, payload_blocks):
    report_lines = [
        "Adaptive BPCS threshold report",
        f"base_alpha = {threshold_info['base_alpha']:.4f}",
        f"min_alpha_prime = {threshold_info['min_alpha_prime']:.4f}",
        f"max_alpha_prime = {threshold_info['max_alpha_prime']:.4f}",
        f"final_threshold = {threshold_info['final_threshold']:.4f}",
        f"payload_blocks = {threshold_info['payload_blocks']}",
        f"conjugated_blocks = {threshold_info['conjugated_blocks']}",
        f"usable_cover_blocks = {threshold_info['usable_cover_blocks']}",
    ]
    Path(THRESHOLD_REPORT).write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    serializable_blocks = []
    for entry in payload_blocks:
        serializable_blocks.append(
            {
                "index": entry["index"],
                "valid_bits": entry["valid_bits"],
                "alpha_before": round(entry["alpha_before"], 6),
                "alpha_after": round(entry["alpha_after"], 6),
                "conjugated": entry["conjugated"],
            }
        )

    Path(MESSAGE_BLOCKS_FILE).write_text(
        json.dumps(
            {
                "secret": SECRET_DATA,
                "block_size": BLOCK_SIZE,
                "base_alpha": BASE_ALPHA,
                "blocks": serializable_blocks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def rebuild_video():
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        f"{FRAMES_DIR}/frame_%04d.png",
    ]
    if Path(AUDIO_FILE).exists():
        cmd += ["-i", AUDIO_FILE, "-c:a", "copy", "-shortest"]
    cmd += ["-c:v", "ffv1", OUTPUT_VIDEO]

    print("Rebuilding video:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def run_analysis():
    _, _, bit_plane, _ = load_target_bit_plane()
    _, payload_blocks = prepare_payload_blocks()
    threshold_info = compute_adaptive_threshold(bit_plane, payload_blocks)
    write_reports(threshold_info, payload_blocks)

    print("ADAPTIVE_ANALYSIS_DONE")
    print(f"min_alpha_prime = {threshold_info['min_alpha_prime']:.4f}")
    print(f"max_alpha_prime = {threshold_info['max_alpha_prime']:.4f}")
    print(f"final_threshold = {threshold_info['final_threshold']:.4f}")
    print(f"conjugated_blocks = {threshold_info['conjugated_blocks']}")


def run_embed():
    frame, channel, bit_plane, frame_path = load_target_bit_plane()
    secret_bits, payload_blocks = prepare_payload_blocks()
    threshold_info = compute_adaptive_threshold(bit_plane, payload_blocks)
    write_reports(threshold_info, payload_blocks)

    if threshold_info["usable_cover_blocks"] < len(payload_blocks):
        raise RuntimeError(
            "Not enough adaptive cover blocks. Lower BASE_ALPHA or choose another frame."
        )

    payload_index = 0
    positions = []
    height, width = bit_plane.shape

    for y, x in iter_block_coords(height, width):
        if payload_index >= len(payload_blocks):
            break

        cover_block = bit_plane[y : y + BLOCK_SIZE, x : x + BLOCK_SIZE]
        cover_alpha = block_complexity(cover_block)
        if cover_alpha < threshold_info["final_threshold"]:
            continue

        payload = payload_blocks[payload_index]
        bit_plane[y : y + BLOCK_SIZE, x : x + BLOCK_SIZE] = payload["block"]
        positions.append(
            {
                "y": int(y),
                "x": int(x),
                "valid_bits": int(payload["valid_bits"]),
                "cover_alpha": round(cover_alpha, 6),
                "alpha_before": round(payload["alpha_before"], 6),
                "alpha_after": round(payload["alpha_after"], 6),
                "conjugated": bool(payload["conjugated"]),
            }
        )
        payload_index += 1

    if payload_index < len(payload_blocks):
        raise RuntimeError(f"Embedded only {payload_index}/{len(payload_blocks)} blocks")

    mask = np.uint8(1 << BIT_PLANE)
    channel = (channel & ~mask) | (bit_plane.astype(np.uint8) << BIT_PLANE)
    frame[:, :, CHANNEL] = channel
    cv2.imwrite(str(frame_path), frame)

    metadata = {
        "method": "Adaptive BPCS with checkerboard conjugation",
        "frame_index": TARGET_FRAME_INDEX,
        "block_size": BLOCK_SIZE,
        "bit_plane": BIT_PLANE,
        "channel": CHANNEL,
        "secret_bit_count": len(secret_bits),
        "threshold": threshold_info,
        "positions": positions,
    }
    Path(POSITION_FILE).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"ADAPTIVE_POSITION_WRITTEN {POSITION_FILE}")
    print(f"Embedded blocks: {len(positions)}")
    print(f"Conjugated blocks: {threshold_info['conjugated_blocks']}")
    rebuild_video()


def main():
    parser = argparse.ArgumentParser(description="Adaptive BPCS encoder")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Compute alpha prime values and adaptive threshold only.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed the secret and rebuild the stego video.",
    )
    args = parser.parse_args()

    if args.analyze and args.embed:
        raise SystemExit("Use only one mode: --analyze or --embed")
    if not args.analyze and not args.embed:
        raise SystemExit("Choose a mode: python3 adaptive_encode.py --analyze")
    if args.analyze:
        run_analysis()
    if args.embed:
        run_embed()


if __name__ == "__main__":
    main()
