#!/usr/bin/env python3
"""End-to-end test: generate WAV -> STT -> LLM -> TTS, all local."""

import sys
import os
import struct
import math
import time

sys.path.insert(0, os.path.dirname(__file__))


def make_test_wav(text_hint: str = "") -> bytes:
    """Generate a short sine-tone WAV (used as placeholder when no real mic input)."""
    sr = 16000
    duration = 1.0
    freq = 440.0
    n = int(sr * duration)
    samples = [int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)]
    data = struct.pack(f"<{n}h", *samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(data), b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", len(data),
    )
    return header + data


def test_stt():
    print("=" * 50)
    print("TEST 1: STT (Whisper)")
    print("=" * 50)
    from moot_brain import hear
    wav = make_test_wav()
    t0 = time.time()
    result = hear(wav)
    elapsed = time.time() - t0
    print(f"  Transcript: '{result}'")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  (Sine tone, so transcript may be empty or noise)")
    print()


def test_llm():
    print("=" * 50)
    print("TEST 2: LLM (Ollama)")
    print("=" * 50)
    from moot_brain import think
    scene = {
        "time_utc": "2026-03-22T12:00:00Z",
        "bodies": [
            {"name": "Sun", "alt_deg": 35.0, "az_deg": 180.0, "distance_au": 1.0},
            {"name": "Moon", "alt_deg": -10.0, "az_deg": 90.0, "distance_au": 0.0026},
        ],
        "lat": 51.5074,
        "lon": -0.1278,
    }
    t0 = time.time()
    result = think("What can I see in the sky right now?", scene)
    elapsed = time.time() - t0
    print(f"  Reply: {result['reply']}")
    print(f"  Actions: {result['actions']}")
    print(f"  Model: {result.get('model')}")
    print(f"  Time: {elapsed:.2f}s")
    print()


def test_tts():
    print("=" * 50)
    print("TEST 3: TTS (F5-TTS + Vocos)")
    print("=" * 50)
    from moot_brain import speak
    t0 = time.time()
    path = speak("Hello! I am Moot, your guide to the stars.")
    elapsed = time.time() - t0
    size = os.path.getsize(path) if os.path.exists(path) else 0
    print(f"  Audio file: {path}")
    print(f"  Size: {size} bytes")
    print(f"  Time: {elapsed:.2f}s")
    print()


def test_full_pipeline():
    print("=" * 50)
    print("TEST 4: Full pipeline (audio -> transcript -> LLM -> TTS)")
    print("=" * 50)
    from moot_brain import process_audio
    wav = make_test_wav()
    t0 = time.time()
    result = process_audio(wav, model="llama3.1:8b", do_tts=True)
    elapsed = time.time() - t0
    print(f"  Transcript: '{result['transcript']}'")
    print(f"  Reply: '{result['reply']}'")
    print(f"  Audio: {result.get('audio_path')}")
    print(f"  Actions: {result.get('actions')}")
    print(f"  Timings: {result.get('timings')}")
    print(f"  Total: {elapsed:.2f}s")
    print()


if __name__ == "__main__":
    print("\nMoot AI Brain — End-to-End Test\n")
    test_llm()
    print("All tests that could complete have completed!")
    print("STT and TTS require GPU model loading (run separately if desired).")
