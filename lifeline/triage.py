"""Shared, dependency-free triage logic: recognize an emergency -> protocol key, plus the
canonical fallback steps. Imported by both the real product (diffusion_server) and the local
preview (mock_ui) so the behavior is identical."""
from __future__ import annotations

CUES = {
    "cpr":   ["not breathing", "isn't breathing", "collapsed", "unresponsive", "no pulse", "cardiac", "heart attack", "passed out", "unconscious"],
    "choke": ["choking", "can't breathe", "cant breathe", "object stuck", "something stuck", "throat"],
    "bleed": ["bleeding", "blood", "cut", "wound", "gushing", "spurting", "hemorrhage"],
    "od":    ["overdose", "opioid", "fentanyl", "heroin", "blue lips", "naloxone", "narcan", "pinpoint"],
    "burn":  ["burn", "burned", "scald", "boiling water", "steam", "fire", "hot water"],
}
CANON = {
    "cpr":   ["Call 911 and get an AED.", "Push hard and fast in the center of the chest, 100-120 per minute, about 2 inches deep.", "Let the chest recoil fully between compressions.", "Continue until an AED or help arrives."],
    "choke": ["Give 5 firm back blows between the shoulder blades.", "Give 5 abdominal thrusts (Heimlich).", "Alternate back blows and thrusts until it clears.", "If they go unconscious, call 911 and start CPR."],
    "bleed": ["Call 911 for severe bleeding.", "Apply firm direct pressure with a clean cloth.", "Do not remove soaked cloths — add more on top.", "If life-threatening limb bleeding, apply a tourniquet above the wound."],
    "od":    ["Call 911.", "Give naloxone (Narcan) if available.", "If not breathing, start rescue breaths or CPR.", "Place them in the recovery position if breathing returns."],
    "burn":  ["Cool the burn under cool running water for 20 minutes.", "Cover loosely with a clean non-stick dressing.", "Do not apply ice or butter, and do not pop blisters."],
}
PROTO_NAME = {"cpr": "Cardiac arrest", "choke": "Choking", "bleed": "Severe bleeding",
              "od": "Opioid overdose", "burn": "Burn"}
URGENT = ["not breathing", "isn't breathing", "unresponsive", "passed out", "unconscious", "no pulse"]
# Explicit opioid signals route to the OD protocol even when the person isn't breathing — the OD
# steps are the correct superset (naloxone + rescue breaths/CPR + 911); plain CPR would miss
# naloxone. Softer od cues ("blue lips","pinpoint") stay in the scorer to avoid over-routing.
OD_HARD = ["overdose", "opioid", "fentanyl", "heroin", "naloxone", "narcan"]


def recognize(t: str):
    t = (t or "").lower()
    if any(c in t for c in OD_HARD):
        return "od"
    if any(u in t for u in URGENT):
        return "cpr"
    best, score = None, 0
    for k, cues in CUES.items():
        s = sum(1 for c in cues if c in t)
        if s > score:
            best, score = k, s
    return best if score else None
