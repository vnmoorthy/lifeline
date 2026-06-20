"""
Map a panicked free-text/spoken utterance to a protocol + a difficulty estimate.

Recognition = keyword match against each protocol's cues (cheap, transparent).
Difficulty = the protocol's base difficulty + a bump per complicating factor — so
"he's choking" is routine but "he's choking and passed out" escalates (more compute).
"""
from __future__ import annotations

from lifeline.protocols import PROTOCOLS

COMPLICATIONS = [
    "unconscious", "passed out", "not breathing", "isn't breathing", "won't stop",
    "soaked", "pregnant", "blue", "seizure", "infant", "baby", "child", "allergic",
    "also", "and ", "elderly", "deep", "spurting", "gushing",
]


def recognize(transcript: str):
    t = (transcript or "").lower()
    best, score = None, 0
    for pid, p in PROTOCOLS.items():
        s = sum(1 for cue in p["cues"] if cue in t)
        if s > score:
            best, score = pid, s
    if best is None or score == 0:
        return None, 0
    bumps = sum(1 for c in COMPLICATIONS if c in t)
    difficulty = PROTOCOLS[best]["base_difficulty"] + 3 * bumps
    return best, difficulty
