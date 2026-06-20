"""Shared, dependency-free triage logic: recognize a spoken emergency -> protocol key, plus the
canonical fallback steps and display names. Imported by the real product (diffusion_server) and
the local preview (mock_ui) so behavior is identical.

Recognition is a principled priority ladder, NOT just keyword counting, because some life-threats
must override the generic "not breathing -> CPR" rule (an opioid overdose or a drowning victim
needs their own protocol, which already includes rescue breathing/CPR). Cues are short keywords
so they substring-match real, varied speech."""
from __future__ import annotations

# Short keyword cues (lowercase) — substring-matched against the transcript.
CUES = {
    "cpr":        ["cardiac", "cardiac arrest", "chest compressions", "heart stopped", "no pulse"],
    "choke":      ["choking", "choke", "something stuck in", "object stuck", "stuck in his throat",
                   "stuck in her throat", "stuck in their throat", "lodged in", "can't swallow"],
    "bleed":      ["bleeding heavily", "bleeding", "bleeding from", "deep cut", "cut", "wound", "gushing",
                   "spurting", "hemorrhage", "laceration", "lots of blood", "lot of blood", "so much blood",
                   "losing blood", "losing a lot of blood", "covered in blood", "blood everywhere",
                   "pool of blood", "blood soaking", "blood gushing", "blood spurting", "blood pouring",
                   "blood coming", "blood running", "blood dripping"],  # NOT bare "blood" (false-matched "blood sugar")
    "od":         ["overdose", "overdosed", "blue lips", "lips are blue", "lips turning blue", "pinpoint", "opioid", "opioids"],
    "burn":       ["burn", "burned", "burnt", "scald", "boiling water", "steam", "hot water", "caught fire", "on fire"],
    "anaphylaxis": ["allergic reaction", "anaphylaxis", "anaphylactic", "epipen", "epi pen", "epinephrine",
                    "auto-injector", "throat closing", "throat is closing", "throat feels like it's closing",
                    "face is swelling", "lips are swelling", "tongue is swelling", "hives", "bee sting", "stung by", "peanut"],
    "stroke":     ["stroke", "face is drooping", "face drooping", "drooping", "slurred", "slurring", "can't speak",
                   "cant speak", "can't talk", "cant talk", "one side of", "numb on one side", "weak on one side",
                   "lift one arm", "arm went weak", "weakness on one side"],
    "seizure":    ["seizure", "seizing", "convuls", "epilep", "having a fit", "jerking", "twitching",
                   "foaming at the mouth", "shaking uncontrollably", "shaking all over", "whole body is shaking", "convulsing"],
    "heart_attack": ["heart attack", "chest pain", "chest pressure", "pressure in my chest", "pressure in his chest",
                     "tightness in my chest", "tightness in his chest", "chest feels heavy", "chest is tight",
                     "crushing", "clutching his chest", "clutching her chest", "clutching their chest",
                     "pain spreading to", "left arm and jaw", "squeezing feeling in"],
    "drown":      ["drowning", "drowned", "aspirated water", "went under water", "underwater", "under water"],
    "hypoglycemia": ["diabetic", "diabetes", "blood sugar", "hypoglycemia", "hypoglycaemia", "low sugar",
                     "sugar is low", "took insulin", "insulin and"],
    "heatstroke": ["heatstroke", "heat stroke", "heat exhaustion", "overheated", "overheating", "in the heat",
                   "from the heat", "the heat and", "burning up", "sunstroke", "hot and dry"],
    "hypothermia": ["hypothermia", "freezing", "frostbite", "ice cold", "shivering", "stopped shivering",
                    "cold to the touch", "out in the cold", "in the cold", "fell into a freezing", "fell into freezing"],
    "poison":     ["poison", "poisonous", "swallowed", "drank bleach", "drank some", "drain cleaner",
                   "cleaning chemical", "cleaning product", "antifreeze", "ate pills", "swallowed pills",
                   "bunch of pills", "ingested", "toxic", "drank chemical"],
    "head_injury": ["hit their head", "hit his head", "hit her head", "hit my head", "head injury", "head trauma",
                    "concussion", "banged their head", "banged his head", "knocked out", "bumped his head",
                    "bumped her head", "fell and hit", "hit head on"],
    "nosebleed":  ["nosebleed", "nose bleed", "bloody nose", "epistaxis"],
    "fracture":   ["broken bone", "broken arm", "broken leg", "broke his", "broke her", "broke my", "fracture",
                   "bone is sticking out", "bone sticking out", "bent the wrong way", "bent at a weird angle",
                   "deformed", "looks crooked", "heard a snap", "compound fracture", "open fracture"],
}

PROTO_NAME = {
    "cpr": "Cardiac arrest", "choke": "Choking", "bleed": "Severe bleeding", "od": "Opioid overdose",
    "burn": "Burn", "anaphylaxis": "Anaphylaxis", "stroke": "Stroke", "seizure": "Seizure",
    "heart_attack": "Heart attack", "drown": "Drowning", "hypoglycemia": "Low blood sugar",
    "heatstroke": "Heat stroke", "hypothermia": "Hypothermia", "poison": "Poisoning",
    "head_injury": "Head injury", "nosebleed": "Nosebleed", "fracture": "Fracture",
}

CANON = {
    "cpr":   ["Call 911 and get an AED.", "Push hard and fast in the center of the chest, 100-120 per minute, about 2 inches deep.", "Let the chest recoil fully between compressions.", "Continue until an AED or help arrives."],
    "choke": ["Give 5 firm back blows between the shoulder blades.", "Give 5 abdominal thrusts (Heimlich).", "Alternate back blows and thrusts until it clears.", "If they go unconscious, call 911 and start CPR."],
    "bleed": ["Call 911 for severe bleeding.", "Apply firm direct pressure with a clean cloth.", "Do not remove soaked cloths — add more on top.", "If life-threatening limb bleeding, apply a tourniquet above the wound."],
    "od":    ["Call 911.", "Give naloxone (Narcan) if available.", "If not breathing, start rescue breaths or CPR.", "Place them in the recovery position if breathing returns."],
    "burn":  ["Cool the burn under cool running water for 20 minutes.", "Cover loosely with a clean non-stick dressing.", "Do not apply ice or butter, and do not pop blisters."],
    "anaphylaxis": [
        "Call 911 (emergency services) immediately and say it is a severe allergic reaction (anaphylaxis).",
        "If the person has an epinephrine auto-injector (such as an EpiPen), help them use it right away: press it firmly against the outer middle thigh and hold for several seconds.",
        "Help them lie down and raise their legs; if they are struggling to breathe, let them sit up, or lie on their side if vomiting. Do not let them stand or walk.",
        "If there is no improvement after 5 minutes and a second auto-injector is available, give a second dose.",
        "Stay with them, monitor their breathing until help arrives, and begin CPR if they stop breathing."],
    "stroke": [
        "Check for FAST signs: Face drooping, Arm weakness, Slurred speech — if any are present it is Time to act.",
        "Call 911 (emergency services) immediately and say you think it is a stroke.",
        "Note the time the symptoms started (or when the person was last known to be normal) and tell the responders.",
        "Help them sit or lie down safely, keep them calm, and do not give them anything to eat or drink.",
        "Monitor their breathing until help arrives, and be ready to start CPR if they become unresponsive."],
    "seizure": [
        "Stay with the person and note the time the seizure starts so you can time how long it lasts.",
        "Clear the area of hard or sharp objects and protect their head by cushioning it with something soft.",
        "Do not restrain them and do not put anything in their mouth.",
        "Call 911 if it lasts longer than 5 minutes, repeats, causes injury, or is their first seizure.",
        "Once the jerking stops, gently roll them onto their side into the recovery position and stay until they are fully alert."],
    "heart_attack": [
        "Call 911 (emergency services) right away and say you think it is a heart attack.",
        "Help the person sit down, keep calm and still, and loosen any tight clothing.",
        "If they are not allergic to aspirin and it is not otherwise unsafe, have them slowly chew one adult aspirin.",
        "Stay with them and monitor closely; if they become unresponsive and stop breathing normally, start CPR.",
        "Keep them calm and reassured until emergency responders arrive."],
    "drown": [
        "Get the person out of the water safely — reach or throw rather than entering dangerous water if you are not a trained rescuer.",
        "Call 911 (emergency services) immediately, or have someone call while you start care.",
        "On dry ground, check whether they are breathing normally.",
        "If they are not breathing, give rescue breaths and start CPR with chest compressions until they recover or help arrives.",
        "If they are breathing, place them on their side in the recovery position, keep them warm, and monitor them."],
    "hypoglycemia": [
        "If they are awake and able to swallow, give about 15 grams of fast-acting sugar — fruit juice, regular (non-diet) soda, glucose tablets, or honey.",
        "Have them sit and rest, wait 15 minutes, and give another 15 grams of fast-acting sugar if they are not better.",
        "Once they improve, give a longer-lasting snack such as crackers or a sandwich.",
        "If they are unconscious or unable to swallow safely, do not give them any food or drink by mouth.",
        "Call 911 (emergency services) if they are unconscious, seizing, or not improving, and place them on their side if unresponsive but breathing."],
    "heatstroke": [
        "Call 911 (emergency services) immediately — heatstroke is life-threatening.",
        "Move the person to a cool, shaded or air-conditioned place and remove excess clothing.",
        "Cool the body aggressively: pour or spray cool water on the skin, put ice packs or cold wet cloths on the neck, armpits, and groin, and fan them.",
        "Do not give anything to drink if they are confused, drowsy, or unconscious; give small sips of cool water only if they are fully alert.",
        "Monitor their breathing until help arrives and be ready to start CPR if they stop breathing normally."],
    "hypothermia": [
        "Call 911 (emergency services) if the person is very cold, confused, drowsy, slurring, or has stopped shivering.",
        "Gently move them to a warm, dry, sheltered place out of the cold and handle them very gently.",
        "Remove any wet clothing and replace it with warm dry layers and blankets, covering the head and neck.",
        "Warm the center of the body with dry blankets or warm compresses — avoid direct high heat such as heating pads or hot water bottles on bare skin.",
        "Do not rub the arms and legs and do not give alcohol; monitor breathing and start CPR if they become unresponsive and are not breathing normally."],
    "poison": [
        "Make sure the scene is safe and the substance is away from the person; call 911 right away if they are unconscious, not breathing, or seizing.",
        "Call Poison Control at 1-800-222-1222 immediately for guidance, and call 911 if the person is seriously ill.",
        "Try to identify what was swallowed and how much, and keep the container or label to show responders.",
        "Do not induce vomiting or give anything by mouth unless Poison Control or 911 tells you to.",
        "Keep them calm, monitor breathing, and begin CPR if they become unresponsive and stop breathing normally."],
    "head_injury": [
        "Call 911 (emergency services) for any red flags: loss of consciousness, repeated vomiting, worsening headache, confusion, slurred speech, seizures, unequal pupils, or fluid from the nose or ears.",
        "Keep the person still and resting; do not let them get up or carry on.",
        "If you suspect a neck or spine injury, do not move their head or neck unless they are in immediate danger.",
        "Monitor their consciousness closely and watch for vomiting, drowsiness, or increasing confusion.",
        "Control any scalp bleeding with gentle pressure using a clean cloth and stay with them until help arrives."],
    "nosebleed": [
        "Sit down and lean forward slightly so blood drains out of the nose, not down the throat — do not tilt the head back.",
        "Pinch the soft part of the nose just below the bony bridge and hold firmly for 10 to 15 minutes without releasing.",
        "Breathe through your mouth and stay calm while keeping steady pressure.",
        "If it is still bleeding after 10 to 15 minutes, pinch again for another 10 to 15 minutes.",
        "Seek emergency help if bleeding will not stop after 20-30 minutes, is very heavy, follows a head injury, or you feel faint."],
    "fracture": [
        "Call 911 (emergency services) for an open fracture (bone through skin), a deformed limb, or a suspected head, neck, back, hip, or thigh injury.",
        "Keep the person still and do not move the injured part; do not try to straighten or realign the bone.",
        "Support and immobilize the injury in the position found, using a splint or padding if available.",
        "Apply an ice pack wrapped in a cloth for about 20 minutes — never put ice directly on bare skin.",
        "Watch for signs of shock, keep them warm and reassured, and stay with them until help arrives."],
}

# Priority overrides (checked before generic scoring) ----------------------------------------
OD_HARD = ["opioid", "opioids", "fentanyl", "heroin", "naloxone", "narcan", "pinpoint"]
# Softer overdose signals: route to OD only when the person is also in arrest/unresponsive — there
# the OD protocol (naloxone + rescue breaths + CPR + recovery position) is the correct superset, and
# empiric naloxone is harmless if it turns out non-opioid. Conscious ingestion stays poison/scoring.
OD_SOFT = ["overdose", "overdosed", "took too much", "took something", "od'd"]
DROWN_CUES = ["drowning", "drowned", "out of the pool", "pulled out of the pool", "out of the water",
              "fell in the pool", "fell in the water", "face down in the water", "out of the lake",
              "out of the ocean", "pulled from the water"]
# Cold-exposure context: 'slurred speech' is both a stroke and a hypothermia sign — a clear cold
# source disambiguates to hypothermia (guarded by 'not arrest', so a not-breathing victim pulled
# from freezing water still goes down the CPR/arrest path).
COLD_EXPOSURE = ["hypothermia", "frostbite", "in the snow", "lost in the snow", "out in the cold",
                 "in the cold for", "ice cold", "cold to the touch", "fell into freezing",
                 "fell into a freezing", "freezing water", "freezing cold", "freezing lake",
                 "exposed to the cold", "stranded in the cold"]
ARREST = ["not breathing", "isn't breathing", "isnt breathing", "stopped breathing", "no pulse"]
DOWN = ["unconscious", "unresponsive", "passed out", "collapsed", "won't wake", "wont wake",
        "not responding", "won't respond", "wont respond", "blacked out", "went limp", "fainted"]
BREATHE_TROUBLE = ["can't breathe", "cant breathe", "can't breath", "struggling to breathe",
                   "trouble breathing", "barely breathe", "hard to breathe"]
CHOKE_OBJECT = ["chok", "stuck", "lodged", "object", "swallowed something"]
# Phrasings that mean it is NOT an active emergency: hypothetical fear ("afraid OF having a stroke",
# distinct from the real "afraid he's having a stroke") or already-resolved ("but he's ok now").
HYPOTHETICAL = ["afraid of having", "worried about having", "scared of having", "afraid of getting",
                "scared of getting", "risk of having", "chance of having", "how to prevent",
                "how do i prevent", "how to avoid", "what if i have", "what if he has", "what if she has"]
RESOLVED = ["but she's ok", "but he's ok", "but they're ok", "but she's fine", "but he's fine",
            "but i'm fine", "but im fine", "but it stopped", "but everything is fine",
            "but seems fine now", "but feels fine now", "but is fine now"]

# Negation handling: a cue only counts if none of the ~3 words just before it is a negation word
# ("no chest pain", "she is not having a stroke", "nothing is stuck" must not route). Word-based,
# not a char window, so "not having a stroke" IS caught while a far-away "no time, ... stroke" is
# NOT (its "no" is >3 words from the cue), which keeps real emergencies from being cancelled.
_NEGWORDS = {"no", "not", "never", "without", "nothing", "none", "cannot", "nope", "neither", "nor",
             "cant", "isnt", "arent", "wont", "dont", "doesnt", "didnt", "wasnt", "werent", "hasnt",
             "havent", "wouldnt", "couldnt", "shouldnt", "aint"}


def _present(t: str, cue: str) -> bool:
    """True if cue appears with no negation word in the ~3 words before it WITHIN ITS CLAUSE — a
    negation in a previous comma/period clause ('not breathing, suspected fentanyl') does not leak in.
    'won't/can't STOP bleeding' is affirmative (continuous), so a negword directly before 'stop' is
    not treated as a negation."""
    i = t.find(cue)
    while i != -1:
        start = max((t.rfind(b, 0, i) + 1) for b in ",.;\n")
        win = t[start:i].replace("'", "").split()[-3:]
        neg = False
        for j, w in enumerate(win):
            if w in _NEGWORDS:
                nxt = win[j + 1] if j + 1 < len(win) else cue
                # "won't STOP" / "didn't PREVENT" / "nothing PREVENTED" are continuation, not negation
                if not (nxt.startswith("stop") or nxt.startswith("prevent")):
                    neg = True
                    break
        if not neg:
            return True
        i = t.find(cue, i + 1)
    return False


def recognize(t: str):
    t = (t or "").lower()
    # 0) Hypothetical ("afraid of having a stroke") or already-resolved ("but he's ok now") -> not an
    #    active emergency; return None so the UI prompts to call 911 only if the caller insists.
    if any(h in t for h in HYPOTHETICAL) or any(r in t for r in RESOLVED):
        return None
    # 1) Specific supersets that already include CPR/rescue breathing must win over generic arrest.
    if any(_present(t, c) for c in OD_HARD):
        return "od"
    if any(_present(t, c) for c in OD_SOFT) and (any(_present(t, a) for a in ARREST) or any(d in t for d in DOWN)):
        return "od"
    if any(_present(t, c) for c in DROWN_CUES):
        return "drown"
    if any(c in t for c in COLD_EXPOSURE) and not any(_present(t, a) for a in ARREST):
        return "hypothermia"
    # 2) Nosebleed: nose + blood, before generic "bleeding" routes to severe-bleed.
    if "nose" in t and ("bleed" in t or "blood" in t):
        return "nosebleed"
    # 3) Breathing difficulty WITH a choking object -> choke. (Bare dyspnea is ambiguous — asthma,
    #    panic, cardiac, anaphylaxis — so it is left to scoring / the 911 fallback, never forced to CPR.)
    if any(_present(t, c) for c in BREATHE_TROUBLE) and any(_present(t, o) for o in CHOKE_OBJECT):
        return "choke"
    # 4) Unconscious choking -> CPR (compressions can clear the airway).
    if _present(t, "chok") and any(d in t for d in DOWN):
        return "cpr"
    # 5) Explicit respiratory/cardiac arrest -> CPR.
    if any(_present(t, a) for a in ARREST):
        return "cpr"
    # 6) Highest-scoring specific protocol.
    scores = {k: sum(1 for c in CUES[k] if _present(t, c)) for k in CUES}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        return best
    # 7) Down with no identified cause and no arrest sign -> None, so the UI says "call 911 and
    #    describe what you see" rather than guessing CPR on someone who may be breathing.
    return None
