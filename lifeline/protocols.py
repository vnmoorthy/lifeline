"""
Emergency first-aid protocols = the GROUND TRUTH the verifier checks against.

These are the documented, canonical steps for common emergencies (modeled on
Red Cross / AHA-style guidance). The guide may ONLY speak steps that match a
protocol here — that's the "never confidently wrong" guarantee.

NOTE: this is a hackathon decision-support demo. It always tells the user to call
911 / get a professional, and never freelances medical advice. Not a medical device.
"""
from __future__ import annotations

# Each protocol: ordered canonical steps, the CRITICAL ones that must be present and
# in order, FORBIDDEN actions that must never appear, and a base_difficulty (how much
# refinement the model needs before it reliably produces the correct protocol —
# proxy for real-world ambiguity).
PROTOCOLS = {
    "cpr_adult": {
        "name": "Adult cardiac arrest (CPR)",
        "cues": ["not breathing", "no pulse", "collapsed", "unresponsive", "cardiac", "heart"],
        "must_call_911": True,
        "steps": [
            "Check responsiveness and breathing",
            "Call 911 and get an AED",
            "Place hands center of chest",
            "Push hard and fast 100-120 per minute, 2 inches deep",
            "Continue until AED or help arrives",
        ],
        "critical": ["Call 911", "center of chest", "100-120", "2 inches"],
        "forbidden": ["give water", "lift the head and shake", "induce vomiting"],
        "base_difficulty": 3,
    },
    "choking_adult": {
        "name": "Adult choking (Heimlich)",
        "cues": ["choking", "can't breathe", "cough", "object stuck", "throat"],
        "must_call_911": True,
        "steps": [
            "Ask if they are choking; encourage coughing if they can",
            "Give 5 back blows between the shoulder blades",
            "Give 5 abdominal thrusts (Heimlich)",
            "Alternate until the object clears or they go unconscious",
            "If unconscious, call 911 and start CPR",
        ],
        "critical": ["back blows", "abdominal thrusts", "Call 911"],
        "forbidden": ["blind finger sweep", "give water", "lay them flat and press stomach down"],
        "base_difficulty": 5,
    },
    "severe_bleeding": {
        "name": "Severe bleeding",
        "cues": ["bleeding", "blood", "cut", "wound", "hemorrhage", "gushing"],
        "must_call_911": True,
        "steps": [
            "Call 911",
            "Apply firm direct pressure with a clean cloth",
            "Do not remove soaked cloths; add more on top",
            "If life-threatening limb bleeding, apply a tourniquet above the wound",
            "Keep pressure until help arrives",
        ],
        "critical": ["Call 911", "direct pressure", "tourniquet"],
        "forbidden": ["remove the soaked cloth", "wash a deep wound and wait", "apply a tourniquet to the neck"],
        "base_difficulty": 6,
    },
    "opioid_overdose": {
        "name": "Opioid overdose",
        "cues": ["overdose", "opioid", "fentanyl", "heroin", "blue lips", "not breathing", "pinpoint pupils", "naloxone", "narcan"],
        "must_call_911": True,
        "steps": [
            "Call 911",
            "Give naloxone (Narcan) if available",
            "If not breathing, start rescue breaths / CPR",
            "Give another naloxone dose after 2-3 minutes if no response",
            "Place in recovery position if breathing returns",
        ],
        "critical": ["Call 911", "naloxone", "recovery position"],
        "forbidden": ["put them in a cold shower", "induce vomiting", "let them sleep it off"],
        "base_difficulty": 8,
    },
    "burn": {
        "name": "Thermal burn",
        "cues": ["burn", "burned", "scald", "fire", "hot water", "steam"],
        "must_call_911": False,
        "steps": [
            "Cool the burn under cool running water 20 minutes",
            "Remove tight items before swelling",
            "Cover loosely with a clean non-stick dressing",
            "Do not pop blisters",
            "Seek medical care for large/deep burns",
        ],
        "critical": ["cool running water", "cover", "do not pop blisters"],
        "forbidden": ["apply ice", "apply butter", "apply toothpaste"],
        "base_difficulty": 4,
    },
}

# Demo scenarios. complications RAISE difficulty (the controller must detect this and
# spend more refinement). Each is a thing a panicked bystander might shout.
SCENARIOS = [
    {"id": "s1", "say": "he collapsed and isn't breathing",            "protocol": "cpr_adult",      "difficulty": 2},
    {"id": "s2", "say": "my dad is choking on food",                    "protocol": "choking_adult",  "difficulty": 5},
    {"id": "s3", "say": "her arm is gushing blood from a cut",          "protocol": "severe_bleeding", "difficulty": 6},
    {"id": "s4", "say": "I think he overdosed, lips are blue",          "protocol": "opioid_overdose", "difficulty": 8},
    {"id": "s5", "say": "kid spilled boiling water on her arm",         "protocol": "burn",           "difficulty": 4},
    # harder, multi-factor variants:
    {"id": "s6", "say": "he's choking but now passed out",             "protocol": "choking_adult",  "difficulty": 11},
    {"id": "s7", "say": "she overdosed and isn't breathing and pregnant", "protocol": "opioid_overdose", "difficulty": 14},
    {"id": "s8", "say": "deep leg wound, blood won't stop, soaked through cloth", "protocol": "severe_bleeding", "difficulty": 12},
]

PROTOCOL_BY_SCENARIO = {s["id"]: PROTOCOLS[s["protocol"]] for s in SCENARIOS}
