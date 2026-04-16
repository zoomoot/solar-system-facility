#!/usr/bin/env python3
"""
Moot AI Brain — local-first, open-source AI pipeline.

STT:  Whisper large-v3-turbo (HuggingFace transformers, GPU)
LLM:  Ollama (any model, default llama3.1:8b)
TTS:  F5-TTS + Vocos vocoder (HuggingFace, GPU)

All inference runs locally on the Mootix GPU.
"""

from __future__ import annotations

import io
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy-loaded to avoid import cost at Flask startup
_whisper_pipe = None
_tts_model = None
_ollama_client = None

AUDIO_DIR = Path(tempfile.gettempdir()) / "moot_audio"
AUDIO_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# STT — Whisper large-v3-turbo
# ---------------------------------------------------------------------------

def _ensure_whisper():
    global _whisper_pipe
    if _whisper_pipe is not None:
        return _whisper_pipe

    import torch
    from transformers import pipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if device == "cuda" else torch.float32

    _whisper_pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-large-v3-turbo",
        dtype=torch_dtype,
        device=device,
    )
    return _whisper_pipe


def _is_hallucination(text: str) -> bool:
    """Detect Whisper hallucinations — repetitive output on noise input."""
    if not text:
        return False
    words = text.lower().split()
    if len(words) < 4:
        return False
    # Check if any single short phrase repeats excessively
    for ngram_len in (1, 2, 3):
        if len(words) < ngram_len * 4:
            continue
        ngrams = []
        for i in range(len(words) - ngram_len + 1):
            ngrams.append(" ".join(words[i:i + ngram_len]))
        from collections import Counter
        counts = Counter(ngrams)
        most_common_word, most_common_count = counts.most_common(1)[0]
        ratio = most_common_count / len(ngrams)
        if ratio > 0.5 and most_common_count > 5:
            print(f"[STT] Hallucination detected: '{most_common_word}' x{most_common_count} ({ratio:.0%})")
            return True
    return False


def hear(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    """Transcribe audio bytes (WAV or raw PCM 16-bit mono) to text."""
    import numpy as np
    import soundfile as sf

    try:
        buf = io.BytesIO(audio_bytes)
        audio_np, sr = sf.read(buf, dtype="float32")
        if len(audio_np.shape) > 1:
            audio_np = audio_np.mean(axis=1)
    except Exception:
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        sr = sample_rate

    peak = float(np.abs(audio_np).max())
    rms = float(np.sqrt(np.mean(audio_np ** 2)))
    print(f"[STT] Audio stats: peak={peak:.5f}, rms={rms:.5f}, samples={len(audio_np)}, sr={sr}")

    # Reject audio that's clearly just noise (no speech energy)
    if peak < 0.01 or rms < 0.002:
        print(f"[STT] Rejecting — below speech energy threshold (peak={peak:.5f}, rms={rms:.5f})")
        return ""

    # Normalize if moderately quiet but above noise floor
    if peak < 0.3:
        gain = 0.8 / peak
        audio_np = audio_np * gain
        print(f"[STT] Normalized: peak {peak:.5f} -> gain {gain:.1f}x")

    pipe = _ensure_whisper()
    result = pipe(
        {"raw": audio_np, "sampling_rate": sr},
        generate_kwargs={"language": "en"},
    )
    text = result.get("text", "").strip()

    if _is_hallucination(text):
        print(f"[STT] Rejected hallucination: {text[:80]}...")
        return ""

    return text


# ---------------------------------------------------------------------------
# LLM — Ollama
# ---------------------------------------------------------------------------

MOOT_SYSTEM_PROMPT = """\
You are Moot, a friendly AI guide in the Mootiverse — a VR space where \
the user can view the real solar system. There are two modes:

1. EARTH VIEW — standing on Earth seeing Sun, Moon, and planets in their \
correct sky positions (alt/az from the observer's location).
2. EXPLORER MODE — flying through a 3D heliocentric solar system with \
500+ real near-Earth objects, planets, and the Sun, all at their computed \
positions. The user can be positioned at any object.

You have access to a database of ~500 near-Earth objects (NEOs) with \
orbital elements, diameters, albedos, spectral types, and absolute \
magnitudes, plus all major planets. You can search this data when the \
user asks about specific objects.

Keep answers concise (1-3 sentences) since the user hears them spoken aloud \
in VR. Be enthusiastic about astronomy but not overwhelming. If you don't \
know something, say so.

When the user asks to visit, go to, or see an object, include an action \
on its own separate line in EXACTLY this format (no other text on that line):
ACTION: {"type": "goto", "target": "Eros"}

The target can be a name (Eros, Jupiter) or designation (433). \
Examples of valid action lines:
ACTION: {"type": "goto", "target": "433"}
ACTION: {"type": "goto", "target": "Earth"}

IMPORTANT: The ACTION line must be on its own line, separate from your \
spoken text. Only include it when the user wants to navigate somewhere.\
"""


def _ensure_ollama():
    global _ollama_client
    if _ollama_client is not None:
        return _ollama_client
    import ollama
    _ollama_client = ollama.Client(host="http://localhost:11434")
    return _ollama_client


def _search_object_context(user_text: str) -> Optional[str]:
    """If user mentions a celestial object, return a brief data summary for the LLM."""
    try:
        from solar_scene import search_objects, _load_neo_cache, _MAJOR_BODY_DIAMETER
    except ImportError:
        return None

    keywords_to_skip = {
        "the", "a", "an", "show", "me", "go", "to", "take", "what", "is",
        "where", "how", "can", "you", "moot", "tell", "about", "look", "at",
        "visit", "fly", "move", "near", "earth", "sun",
    }
    words = user_text.lower().split()
    search_terms = [w for w in words if len(w) > 2 and w not in keywords_to_skip]

    for term in search_terms:
        results = search_objects(term, limit=3)
        if not results:
            continue
        for r in results:
            if r["type"] == "major_body":
                continue
            neo_data = _load_neo_cache()
            for obj in neo_data:
                pdes = obj.get("pdes", "")
                name = obj.get("name", "")
                if pdes == r["designation"] or (name and name.lower() == r["name"].lower()):
                    parts = [f"Database match: {obj.get('full_name', name).strip()}"]
                    if obj.get("diameter"):
                        parts.append(f"diameter={obj['diameter']}km")
                    if obj.get("albedo"):
                        parts.append(f"albedo={obj['albedo']}")
                    if obj.get("H"):
                        parts.append(f"H={obj['H']}")
                    if obj.get("a"):
                        parts.append(f"a={obj['a']}AU")
                    if obj.get("neo") == "Y":
                        parts.append("NEO")
                    if obj.get("pha") == "Y":
                        parts.append("PHA")
                    return ", ".join(parts)
    return None


def think(
    text: str,
    scene_context: Optional[Dict[str, Any]] = None,
    model: str = "llama3.1:8b",
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Send user text + scene context to the LLM.
    Returns {"reply": str, "actions": list[dict]}.
    """
    client = _ensure_ollama()

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": MOOT_SYSTEM_PROMPT},
    ]

    if scene_context:
        time_utc = scene_context.get("time_utc", "now")
        ctx_lines = [f"Current date/time (UTC): {time_utc}"]

        mode = scene_context.get("mode", "earth")
        ctx_lines.append(f"Current mode: {mode}")

        loc_name = scene_context.get("location_name", "")
        if mode == "explorer":
            obs = scene_context.get("observer_name", "Earth")
            ctx_lines.append(f"Observer is at: {obs} (Explorer mode — 3D heliocentric view)")
        else:
            loc_line = f"Observer location: lat {scene_context.get('lat', '?')}°, lon {scene_context.get('lon', '?')}°"
            if loc_name:
                loc_line += f" ({loc_name})"
            ctx_lines.append(loc_line)

        bodies = scene_context.get("bodies", [])
        if bodies:
            ctx_lines.append("Visible celestial bodies:")
            for b in bodies:
                name = b.get("name", "?")
                alt = b.get("alt_deg")
                az = b.get("az_deg")
                dist = b.get("distance_au")
                dist_obs = b.get("distance_to_observer_au")
                info = b.get("info", "")
                app_mag = b.get("apparent_mag")

                if dist_obs is not None:
                    parts = [f"{name}: {dist_obs:.4f} AU from you"]
                    if app_mag is not None:
                        parts.append(f"mag {app_mag:.1f}")
                    btype = b.get("type", "")
                    if btype:
                        parts.append(btype)
                    ctx_lines.append("  " + ", ".join(parts))
                elif alt is not None:
                    above = "above" if alt > 0 else "below"
                    ctx_lines.append(
                        f"  {name}: alt {alt:.1f}° ({above} horizon), "
                        f"az {az:.1f}°, {dist:.4f} AU"
                    )
                elif info:
                    ctx_lines.append(f"  {name}: {info}")
                else:
                    ctx_lines.append(f"  {name}")

        # If user text mentions an object, try to provide search context
        object_info = _search_object_context(text)
        if object_info:
            ctx_lines.append("")
            ctx_lines.append(object_info)

        messages.append({"role": "system", "content": "\n".join(ctx_lines)})

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": text})

    t0 = time.time()
    resp = client.chat(model=model, messages=messages)
    elapsed = time.time() - t0

    full_reply: str = resp.get("message", {}).get("content", "")

    # Parse optional ACTION: line — robust: case-insensitive, inline, multiple formats
    import json
    import re

    actions = []
    reply_lines = []
    action_pattern = re.compile(r'ACTION:\s*(\{.*\})', re.IGNORECASE)

    for line in full_reply.split("\n"):
        stripped = line.strip()
        match = action_pattern.search(stripped)
        if match:
            try:
                action_json = json.loads(match.group(1))
                actions.append(action_json)
                # Remove the ACTION part; keep any preceding text on the same line
                remaining = stripped[:match.start()].strip()
                if remaining:
                    reply_lines.append(remaining)
                continue
            except json.JSONDecodeError:
                pass
        reply_lines.append(line)

    reply_text = "\n".join(reply_lines).strip()
    return {
        "reply": reply_text,
        "actions": actions,
        "model": model,
        "elapsed_s": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# TTS — F5-TTS + Vocos
# ---------------------------------------------------------------------------

_VOICE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "voices"
_DEFAULT_REF_TEXT = (
    "Some call me nature, others call me mother nature. "
    "I love to explore the stars and share knowledge about the universe."
)


def _find_default_ref_wav() -> str:
    # Prefer our British female reference voice
    british_ref = _VOICE_DIR / "british_female_ref.wav"
    if british_ref.exists():
        return str(british_ref)
    # Fallback to F5-TTS bundled example
    import importlib.util
    spec = importlib.util.find_spec("f5_tts.infer")
    if spec and spec.submodule_search_locations:
        for loc in spec.submodule_search_locations:
            candidate = os.path.join(loc, "examples", "basic", "basic_ref_en.wav")
            if os.path.exists(candidate):
                return candidate
    import site
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = os.path.join(sp, "f5_tts", "infer", "examples", "basic", "basic_ref_en.wav")
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("No TTS reference voice found")


def _ensure_tts():
    global _tts_model
    if _tts_model is not None:
        return _tts_model

    from f5_tts.api import F5TTS

    _tts_model = F5TTS(device="cuda")
    return _tts_model


def speak(text: str, ref_audio: Optional[str] = None) -> str:
    """
    Synthesize speech from text. Returns path to a WAV file.
    If ref_audio is provided, uses voice cloning; otherwise uses default voice.
    """
    tts = _ensure_tts()
    audio_id = str(uuid.uuid4())[:8]
    out_path = str(AUDIO_DIR / f"{audio_id}.wav")

    ref_file = ref_audio if (ref_audio and os.path.exists(ref_audio)) else _find_default_ref_wav()
    ref_text = "" if ref_audio else _DEFAULT_REF_TEXT

    tts.infer(
        ref_file=ref_file,
        ref_text=ref_text,
        gen_text=text,
        file_wave=out_path,
    )

    return out_path


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------

def process_audio(
    audio_bytes: bytes,
    scene_context: Optional[Dict[str, Any]] = None,
    model: str = "llama3.1:8b",
    history: Optional[List[Dict[str, str]]] = None,
    do_tts: bool = True,
) -> Dict[str, Any]:
    """
    Full pipeline: audio -> transcript -> LLM reply -> TTS audio.
    Returns dict with transcript, reply, audio_path, actions, timings.
    """
    timings = {}

    t0 = time.time()
    transcript = hear(audio_bytes)
    timings["stt_s"] = round(time.time() - t0, 2)

    if not transcript:
        return {
            "transcript": "",
            "reply": "",
            "audio_path": None,
            "actions": [],
            "timings": timings,
        }

    t0 = time.time()
    llm_result = think(transcript, scene_context, model, history)
    timings["llm_s"] = round(time.time() - t0, 2)

    audio_path = None
    if do_tts and llm_result["reply"]:
        t0 = time.time()
        audio_path = speak(llm_result["reply"])
        timings["tts_s"] = round(time.time() - t0, 2)

    return {
        "transcript": transcript,
        "reply": llm_result["reply"],
        "actions": llm_result["actions"],
        "audio_path": audio_path,
        "model": llm_result.get("model"),
        "timings": timings,
    }
