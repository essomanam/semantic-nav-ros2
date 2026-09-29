"""Natural-language command -> structured goal (no ROS dependency).

Design choice: the LLM only *parses* the sentence into
``{"label": <COCO class>, "criterion": "nearest" | "farthest"}``.
Target selection and navigation stay deterministic. This keeps the system
testable and avoids the LLM hallucinating coordinates.

If the LLM is unavailable or returns something invalid, a keyword parser
takes over, so the robot never depends on the LLM to work.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

# French (and a few English) words -> COCO class names used by YOLO.
SYNONYMS = {
    "chaise": "chair", "chaises": "chair", "chair": "chair",
    "table": "dining table", "tables": "dining table",
    "canape": "couch", "sofa": "couch", "couch": "couch",
    "plante": "potted plant", "plantes": "potted plant", "plant": "potted plant",
    "personne": "person", "humain": "person", "person": "person",
    "bouteille": "bottle", "bottle": "bottle",
    "television": "tv", "tele": "tv", "ecran": "tv", "tv": "tv",
    "lit": "bed", "bed": "bed",
    "frigo": "refrigerator", "refrigerateur": "refrigerator",
}

FARTHEST_PATTERNS = ("plus loin", "plus eloign", "farthest", "furthest")


@dataclass
class ParsedCommand:
    label: str
    criterion: str = "nearest"
    source: str = "keywords"   # "llm" or "keywords", useful for evaluation


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def parse_with_keywords(text: str, known_labels: Iterable[str]) -> Optional[ParsedCommand]:
    norm = _normalize(text)
    known = set(known_labels)
    criterion = "farthest" if any(p in norm for p in FARTHEST_PATTERNS) else "nearest"
    for word in re.findall(r"[a-z]+", norm):
        label = SYNONYMS.get(word)
        if label and (not known or label in known):
            return ParsedCommand(label, criterion, "keywords")
    for label in known:  # direct match on a known class name ("dining table"...)
        if label in norm:
            return ParsedCommand(label, criterion, "keywords")
    return None


def build_prompt(text: str, known_labels: Iterable[str]) -> str:
    labels = ", ".join(sorted(known_labels))
    return (
        "You convert a robot command into JSON.\n"
        f"Allowed labels: [{labels}].\n"
        'Answer ONLY with {"label": <one allowed label>, '
        '"criterion": "nearest" or "farthest"}.\n'
        'If no allowed label matches, answer {"label": null, "criterion": "nearest"}.\n'
        f"Command: {text}"
    )


def parse_llm_answer(answer: str, known_labels: Iterable[str]) -> Optional[ParsedCommand]:
    try:
        data = json.loads(answer)
    except (json.JSONDecodeError, TypeError):
        return None
    label = data.get("label")
    criterion = data.get("criterion", "nearest")
    if label not in set(known_labels):
        return None
    if criterion not in ("nearest", "farthest"):
        criterion = "nearest"
    return ParsedCommand(label, criterion, "llm")


def parse_command(
    text: str, known_labels: Iterable[str],
    llm: Optional[Callable[[str], str]] = None,
) -> Optional[ParsedCommand]:
    known = list(known_labels)
    if llm is not None and known:
        try:
            parsed = parse_llm_answer(llm(build_prompt(text, known)), known)
            if parsed:
                return parsed
        except Exception:  # network error, timeout...: fall back silently
            pass
    return parse_with_keywords(text, known)


def ollama_client(model: str = "qwen2.5:3b", url: str = "http://localhost:11434",
                  timeout: float = 20.0) -> Callable[[str], str]:
    """Return a callable prompt -> raw JSON string, backed by a local Ollama server."""
    def _call(prompt: str) -> str:
        body = json.dumps({"model": model, "prompt": prompt,
                           "format": "json", "stream": False}).encode()
        req = urllib.request.Request(f"{url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())["response"]
    return _call
