"""ElevenLabs helpers for Bullchip Banter. Key lives in C:\\Users\\Chip\\Tools\\elevenlabs_key.txt.

python assets/banter/eleven.py clone      clone Chip's voice from his NaturalReader recordings
python assets/banter/eleven.py search <accent> [<gender>] [<query>]   search the shared voice library
"""
import json
import sys
from pathlib import Path

import requests

KEY = Path(r"C:\Users\Chip\Tools\elevenlabs_key.txt").read_text().strip()
API = "https://api.elevenlabs.io/v1"
H = {"xi-api-key": KEY}
BUCKY = Path(r"\\SERVER01\Folder Redirection\Chip\Documents\1 SUBSTACK\Bucky DaBull")
VOICES = Path(__file__).parent / "eleven_voices.json"  # role -> voice_id, the cast sheet


def cast():
    return json.loads(VOICES.read_text()) if VOICES.exists() else {}


def save_cast(c):
    VOICES.write_text(json.dumps(c, indent=1))


def clone():
    """Clone Chip's voice. remove_background_noise strips the room echo in his NaturalReader exports."""
    files = [BUCKY / n for n in ("host intro.mp3", "host intro v1.mp3", "host outro.mp3")]
    r = requests.post(f"{API}/voices/add", headers=H, data={"name": "Chip Corley host", "remove_background_noise": "true",
                      "description": "Chip Corley, Bullchip Banter host"},
                      files=[("files", (f.name, f.read_bytes(), "audio/mpeg")) for f in files])
    r.raise_for_status()
    c = cast()
    c["HOST"] = r.json()["voice_id"]
    save_cast(c)
    print("HOST", c["HOST"])


def search(accent, gender="male", query=""):
    p = {"accent": accent, "gender": gender, "search": query, "page_size": 30, "sort": "usage_character_count_1y"}
    r = requests.get(f"{API}/shared-voices", headers=H, params={k: v for k, v in p.items() if v})
    r.raise_for_status()
    for v in r.json()["voices"]:
        print(v["voice_id"], v["public_owner_id"], "|", v["name"], "|", v.get("age"), v.get("accent"), v.get("use_case"),
              "|", (v.get("description") or "")[:110].replace("\n", " "))


MODEL = "eleven_v4"

# role -> library candidates (public_owner_id, voice_id, name), picked against Chip's personality brief
CANDIDATES = {
    "BUCKY": [("", "15CVCzDByBinCIoCblXo", "Lucan Rook, energetic"), ("", "34lPwSZ54D8fWbX1aHzk", "Guy, upbeat announcer")],
    "BITME": [("", "XaRY1hVbOF8v4zmguHdl", "Sterling, deep cynic"), ("", "LysucvtFmzi1NVAE0rKp", "Marshal, dry and grumpy")],
    "DUHBURRO": [("", "SDARFhQygpPvpLh7Ad1B", "Odd Todd, nervous"), ("", "JSV4pJFuHRMCWZTxkpoQ", "Snorre, jittery")],
    "DUHELEFANTE": [("", "XAezqB2SuTKEhjCMe7Oy", "Roger, laid back"), ("", "gyIv9PAQRvJjSZlk68oE", "Darius, smooth")],
    "BADASK": [("", "pSfivq1mIHnYTVwluxnz", "Carter, rugged"), ("", "TjO2L33VfWYPVuCxsbC4", "Vinnie, edgy Londoner")],
    "HOOTER": [("", "Aaz7hX6MUrjjm0ncqvAg", "Sir Stephen, cinematic"), ("", "jAW0IMxOTz75sgLAYWp6", "Desmond, distinguished")],
    "BOSSHOG": [("", "2gfDLuf2nZfSrUuWQo1W", "Hank Turner, Southern"), ("", "8kvxG72xUMYnIFhZYwWj", "Billy Bob, Southern")],
    "CAPO": [("", "s2wvuS7SwITYg8dqsJdn", "Antonio, old Italian"), ("", "QzTKubutNn9TjrB7Xb2Q", "Jerry B, New York Italian")],
    "LEPHEWY": [("", "K8nDX2f6wjv6bCh5UeZi", "Jamie, French accent"), ("", "bFr1v73huN7dLcVKbWRD", "Gaetan, French accent")],
}


def owner(voice_id, name):
    r = requests.get(f"{API}/shared-voices", headers=H, params={"search": name.split(",")[0], "page_size": 100})
    for v in r.json()["voices"]:
        if v["voice_id"] == voice_id:
            return v["public_owner_id"]
    raise LookupError(voice_id)


def add_shared(voice_id, desc, name):
    r = requests.post(f"{API}/voices/add/{owner(voice_id, desc)}/{voice_id}", headers=H, json={"new_name": name})
    r.raise_for_status()
    return r.json()["voice_id"]


def delete_voice(voice_id):
    requests.delete(f"{API}/voices/{voice_id}", headers=H).raise_for_status()


def speak(voice_id, text, out, stability=0.4, style=0.35):
    r = requests.post(f"{API}/text-to-speech/{voice_id}", headers=H, params={"output_format": "mp3_44100_128"},
                      json={"text": text, "model_id": MODEL,
                            "voice_settings": {"stability": stability, "similarity_boost": 0.8, "style": style}})
    r.raise_for_status()
    Path(out).write_bytes(r.content)


def audition(cands=None, reel_name="Bullchip Banter ElevenLabs audition 2026-10-22.mp3"):
    sys.argv = ["x"]
    import build_episode as b
    host = cast()["HOST"]
    reel = BUCKY / reel_name
    b.silence(0.5, b.WORK / "gap.wav")
    b.silence(1.2, b.WORK / "gap_long.wav")
    parts, labels = [], {}
    for role, opts in (cands or CANDIDATES).items():
        for n, (_, vid, desc) in enumerate(opts, 1):
            tag, line = b.WORK / f"el_{role}_{n}_tag.mp3", b.WORK / f"el_{role}_{n}.mp3"
            speak(host, f"{b.LABEL[role]}. Option {n}.", tag, stability=0.6, style=0.2)
            tmp = add_shared(vid, desc, f"audition {role} {n}")
            try:
                speak(tmp, b.SAMPLES[role], line)
            finally:
                delete_voice(tmp)
            for f in (tag, line):
                b.to_wav(f, f.with_suffix(".wav"))
            parts += [tag.with_suffix(".wav"), b.WORK / "gap.wav", line.with_suffix(".wav"), b.WORK / "gap_long.wav"]
            labels[f"{role} {n}"] = desc
            print(role, n, desc, flush=True)
    b.concat(parts, reel)
    print(reel)


# Round 2, Oct 22 2026: Chip passed on both Bit Me and Hooter voices in round 1.
ROUND2 = {
    "BITME": [("", "GPj7TWARaf5fPNhxhOI6", "Darius, grumpy and critical"), ("", "yrT1876dlfqwBq29bT4p", "Thomas, raspy and skeptical"),
              ("", "mSOmKHC6GZcZbSTGlqHO", "Mister Gruff, miserable old neighbor")],
    "HOOTER": [("", "i6icHCFicH3kzHTat04x", "Richard Basston, regal"), ("", "b1A9OAVD1Yu0SjoFdv4A", "Raymond, theatrical classical"),
               ("", "UlQzP061AqptrSLuYnFf", "Baron Theatricus, dramatic elocution")],
}


def lock_cast():
    """Save Capo's designed voice and add every picked library voice to the account (10-voice limit)."""
    c = cast()
    if "CAPO" not in c:
        gid = (Path(__file__).parent / "_episode_work" / "capo_bk_design_ids.txt").read_text().split()[2]
        r = requests.post(f"{API}/text-to-voice", headers=H, json={
            "voice_name": "Capo DaWolf", "generated_voice_id": gid,
            "voice_description": "Sixty-year-old Italian-American mob boss from Brooklyn. Thick Brooklyn accent, deep, gravelly, slow, quiet menace."})
        r.raise_for_status()
        c["CAPO"] = r.json()["voice_id"]
    picks = json.loads((Path(__file__).parent / "eleven_picks.json").read_text(encoding="utf-8-sig"))
    for role, (vid, desc) in picks.items():
        if role not in c:
            c[role] = add_shared(vid, desc, f"Bucky's Blokes {role}")
    save_cast(c)
    print(json.dumps(c, indent=1))


# Per-role delivery: lower stability = more expressive; higher style = more character.
DELIVERY = {"HOST": (0.55, 0.25), "DUHBURRO": (0.3, 0.5), "DUHELEFANTE": (0.6, 0.2), "BUCKY": (0.35, 0.5),
            "BITME": (0.45, 0.4), "HOOTER": (0.5, 0.45), "BADASK": (0.4, 0.4), "BOSSHOG": (0.4, 0.45),
            "CAPO": (0.5, 0.35), "LEPHEWY": (0.35, 0.5)}
INTRO_TXT = BUCKY / "Host intro VOICE - Duhs at the Roundtable 2026-10-25.txt"
OUTRO_TXT = BUCKY / "Host outro VOICE v2 - Duhs at the Roundtable 2026-10-25.txt"
EPISODE = BUCKY / "Bullchip Banter - Duhs at the Roundtable ELEVENLABS 2026-10-25.mp3"


def paragraphs(path):
    return [" ".join(p.split("\n")) for p in path.read_text(encoding="utf-8").strip().split("\n\n")]


def episode():
    """Intro and outro in Chip's clone, one paragraph at a time; then the hosted roundtable."""
    sys.argv = ["x"]
    import build_episode as b
    c = cast()
    b.silence(0.35, b.WORK / "e_gap.wav")
    b.silence(0.7, b.WORK / "e_para.wav")
    b.silence(1.2, b.WORK / "e_long.wav")
    segs = [("HOST", t, "e_para") for t in paragraphs(INTRO_TXT)]
    segs[-1] = segs[-1][:2] + ("e_long",)
    # A beat before each host bridge, so the hand-off lands; quick back-and-forth between guests.
    segs += [(w, t, "e_para" if i + 1 < len(b.LINES) and b.LINES[i + 1][0] == "HOST" else "e_gap")
             for i, (w, t) in enumerate(b.LINES)]
    segs[-1] = segs[-1][:2] + ("e_long",)
    segs += [("HOST", t, "e_para") for t in paragraphs(OUTRO_TXT)]
    parts = []
    import hashlib
    for i, (who, text, gap) in enumerate(segs, 1):
        # Keyed by speaker + text: an edited line re-voices, every unchanged line reuses its take.
        mp3 = b.WORK / f"h_{hashlib.md5((who + '|' + text).encode()).hexdigest()[:12]}_{who}.mp3"
        if not mp3.exists():
            stab, style = DELIVERY[who]
            speak(c[who], text, mp3, stab, style)
        b.to_wav(mp3, mp3.with_suffix(".wav"))
        parts += [mp3.with_suffix(".wav"), b.WORK / f"{gap}.wav"]
        print(i, who, flush=True)
    # Each build gets its time in the name, so Chip can tell versions apart in the folder.
    import datetime
    out = EPISODE.with_name(f"{EPISODE.stem} built {datetime.datetime.now():%H%M}.mp3")
    b.concat(parts[:-1], out)
    print(out)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    {"clone": clone, "search": search, "audition": audition, "lock": lock_cast, "episode": episode,
     "round2": lambda: audition(ROUND2, "Bullchip Banter ElevenLabs audition round 2 2026-10-22.mp3")}[sys.argv[1]](*sys.argv[2:])
