"""Build a multi-voice Bullchip Banter episode, hosted by Chip.

python assets/banter/build_episode.py            build the episode
python assets/banter/build_episode.py audition   build the voice audition reel

The intro is Chip's own NaturalReader recording (host intro.mp3). Every HOST line and
the outro are voiced by clone_host.py, cloned from about 15 seconds of that intro.
Character lines are voiced with Microsoft neural voices (edge-tts).
"""
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
import imageio_ffmpeg

BUCKY = Path(r"\\SERVER01\Folder Redirection\Chip\Documents\1 SUBSTACK\Bucky DaBull")
WORK = Path(__file__).parent / "_episode_work"
WORK.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = BUCKY / "Bullchip Banter - Duhs at the Roundtable EPISODE v2 2026-10-25.mp3"
REEL = BUCKY / "Bullchip Banter voice audition 2026-10-22.mp3"

# Personality brief -> (voice, rate, pitch). Two candidates each; Chip picks by ear.
CANDIDATES = {
    "BUCKY": [("en-US-GuyNeural", "+8%", "+2Hz"), ("en-US-AndrewNeural", "+10%", "+3Hz")],  # dynamic
    "BITME": [("en-US-RogerNeural", "-8%", "-8Hz"), ("en-US-SteffanNeural", "-10%", "-6Hz")],  # cynical
    "DUHBURRO": [("en-US-ChristopherNeural", "+18%", "+6Hz"), ("en-US-EricNeural", "+20%", "+8Hz")],  # high strung
    "DUHELEFANTE": [("en-US-BrianNeural", "-14%", "-6Hz"), ("en-US-AndrewMultilingualNeural", "-14%", "-8Hz")],  # laid back
    "BADASK": [("en-AU-WilliamMultilingualNeural", "+10%", "+0Hz"), ("en-IE-ConnorNeural", "+10%", "-2Hz")],  # edgy
    "HOOTER": [("en-GB-RyanNeural", "-12%", "-4Hz"), ("en-GB-ThomasNeural", "-12%", "-4Hz")],  # Roman senator
    "BOSSHOG": [("en-US-EricNeural", "-14%", "-10Hz"), ("en-US-BrianMultilingualNeural", "-16%", "-10Hz")],  # Southern (no Southern voice exists)
    "CAPO": [("it-IT-DiegoNeural", "-12%", "-10Hz"), ("it-IT-GiuseppeMultilingualNeural", "-14%", "-10Hz")],  # Godfather
    "LEPHEWY": [("fr-FR-HenriNeural", "-2%", "+2Hz"), ("fr-FR-RemyMultilingualNeural", "-2%", "+2Hz")],  # French
}
PICK = {k: 0 for k in CANDIDATES}  # set to Chip's choices after the audition

SAMPLES = {
    "BUCKY": "Retail sales? Up more than six percent! Builders build, Chip. That's what we do!",
    "BITME": "Oh, I'm just enjoying the show. Let's blame each other. That always brings prices down.",
    "DUHBURRO": "Okay. Okay. Okay! Prices are up nearly four percent. Who did that? Not us. Not us!",
    "DUHELEFANTE": "Now, now. Easy, Burro. Have a seat. Not us either. We were out to lunch.",
    "BADASK": "Itching? I'm furious. Diesel tops six dollars a gallon. So who pays? You do.",
    "HOOTER": "Friends. Colleagues. Citizens of the market. The numbers do not campaign. They simply testify.",
    "BOSSHOG": "Well, I'll be. Y'all are just now getting to the good part. Somebody's fixing to hand out checks.",
    "CAPO": "Nobody elected me. That's why I'm still here. It's not personal. It's just the bond market.",
    "LEPHEWY": "Messieurs! Bonjour, bonjour. I have here a little coin. It hedges everything. Guaranteed.",
}
LABEL = {
    "BUCKY": "Bucky Da Bull", "BITME": "Bit Me Da Bear", "DUHBURRO": "Duh Burro, the donkey",
    "DUHELEFANTE": "Duh Ella-fahn-tay, the elephant", "BADASK": "Bad Ask, the badger", "HOOTER": "Hooter, the owl",
    "BOSSHOG": "Boss Hog", "CAPO": "Capo Da Wolf", "LEPHEWY": "Le Phooey, the polecat",
}

# Spoken script: rounded numbers, voice-safe names, no heteronyms. HOST = Chip's voice.
# Six questions, in the order the intro promises. Every HOST line closes the last topic, bridges to the
# next, and hands off by name. Each guest opens by answering the speaker before them.
LINES = [
    # 1. Inflation
    ("HOST", "Question one. Inflation. Duh Burro. Old Lefty. Our left-leaning socialist. You asked for the microphone, so you go first. Prices are up. Who did it?"),
    ("DUHBURRO", "Thank you, Chip! Okay. Okay. Folks, prices are up nearly four percent from a year ago. Four percent! Who did that? Not us. Not us! Greedy corporations did that!"),
    ("HOST", "That's one side. Duh Ella-fahn-tay. Old Righty. Our right-leaning nationalist. You hold the gavel. Same question. Who did it?"),
    ("DUHELEFANTE", "Now, now. Easy, Burro. Have a seat. Not us either. Blame foreign oil. Put it in writing. We were out to lunch. Long lunch."),
    ("HOST", "Two answers. Both of them, not us. So let's ask somebody who keeps score. Hooter. You keep the books. What do they say?"),
    ("HOOTER", "Friends. Colleagues. Citizens of the market. In September alone, prices climbed more than half a percent. Gasoline did the heaviest lifting. Strip out food and energy, and core inflation sits under three percent. The numbers do not campaign. They simply testify."),
    ("HOST", "Burro. You're shaking your head."),
    ("DUHBURRO", "Core? Hooter, with respect. Nobody eats core! Nobody drives core!"),
    ("DUHELEFANTE", "Old Righty has to admit it. For once, my donkey friend is right. Strike that. Pretend I never said it."),
    # 2. Diesel
    ("HOST", "Hold that thought. The Burro just made our next point for us. Nobody drives core. They drive on diesel. That's question two. Bad Ask, you've been itching to jump in. Diesel. Go."),
    ("BADASK", "Itching? I'm furious. Hooter says gasoline did the heavy lifting. Diesel did worse. Diesel tops six dollars a gallon. A year ago, under four. That's up nearly three quarters. Trucks, tractors, freight trains. They all burn it. So who pays? You do. Every time you buy groceries."),
    ("DUHBURRO", "Six dollars! And the Burro blames the elephant's side!"),
    ("DUHELEFANTE", "And Old Righty blames the donkey's side. See, Chip? Bipartisan."),
    # 3. War
    ("HOST", "Bipartisan blame. But diesel comes from crude oil. And crude comes from a part of the world neither party controls. That's question three. The war. Bit Me Da Bear. You've been quiet. That usually means trouble."),
    ("BITME", "Oh, I'm just enjoying the show. Bad Ask asked who pays. Start with who's shooting. Brent crude, about a hundred and fifteen dollars a barrel. A year ago, about sixty. Earlier this month, it touched a hundred and thirty. The war with Iran began in February. But sure. Let's blame each other. That always brings prices down."),
    # 4. Interest rates
    ("HOST", "So let me add it up. Prices up. Diesel up. Oil up. And a war nobody can end by November. Burro. Elephant. You can't stop a war in nine days. What can you do?"),
    ("DUHBURRO", "The Burro says, lower interest rates! Lower rates before November third! Before! Not after!"),
    ("DUHELEFANTE", "Old Righty seconds it. All in favor? Unanimous. Well, that was easy."),
    ("HOST", "And that's question four. Interest rates. Here's the problem with that plan. Washington doesn't set every rate. Some rates get set at the far end of this table. Capo Da Wolf. You heard the motion."),
    ("CAPO", "I heard it. Unanimous. Cute. Burro. Elephant. You vote. We price. The Fed holds the short rate near four percent. Fine. But the ten-year Treasury pays more than five. That rate is ours."),
    ("DUHBURRO", "The Burro wants to know. Who elected you, wolf?"),
    ("CAPO", "Nobody elected me, Burro. That's why I'm still here. Mortgages cost more than seven percent. The debt is nearly forty trillion dollars. The interest bill tops a trillion dollars a year. More than defense. It's not personal. It's just the bond market. Capisce?"),
    ("DUHELEFANTE", "A trillion for interest? Well, now. Old Righty has to ask. Who borrowed all that?"),
    ("HOST", "And right on cue, the elephant points at the donkey. The donkey points right back. Hooter, you've read the ledger. Who's right?"),
    ("HOOTER", "Both. The ledger carries two signatures. History is patient, gentlemen. So are your creditors. Until they are not."),
    # 5. Redistribution
    ("HOST", "Patient, until they're not. Now, I don't think our friends from Washington heard a word of that. Because there's an election in nine days. And that's question five. Redistribution. Who gets a check? Which brings us to Boss Hog. Boss, what's on the menu?"),
    ("BOSSHOG", "Well, I'll be. Y'all are just now getting to the good part. Nine days, fellas. Somebody's fixing to hand out checks. Now who's buying?"),
    ("DUHBURRO", "The Burro has it. A diesel rebate! Spread the wealth!"),
    ("DUHELEFANTE", "Old Righty sees your rebate. A gas tax holiday. And a tariff on foreign oil. America first."),
    ("BOSSHOG", "Now that's what I call a barbecue. Pass the plate."),
    ("CAPO", "Capo Da Wolf again. And paid for with what, gentlemen? More bonds? Yours."),
    ("HOST", "That's Capo, from the far end of the table. For our listeners. On a bond desk, Yours means I sold, you bought. Every time Washington borrows, somebody has to buy. And whenever free money hits the table, somebody shows up to collect. Hold on. We have a late arrival. Le Phooey."),
    ("LEPHEWY", "Messieurs! Bonjour, bonjour. I hear there is free money? Bon. I have here a little coin. It hedges inflation. It hedges diesel. It hedges elections. Guaranteed. Mon ami, you want in?"),
    ("HOST", "Bad Ask. You did the diesel math. Check his."),
    ("BADASK", "Bitcoin is about eighty-two thousand dollars. A year ago, about a hundred and seven thousand. Down nearly a quarter. Some hedge, Le Phooey."),
    ("LEPHEWY", "Ah. Well. Past performance, it is no guarantee. Au revoir!"),
    ("HOST", "And just like that, the polecat is gone. Check your wallet. Now. We've heard a lot of bad news at this table. Prices. Diesel. Oil. Debt. Bucky Da Bull, you've waited long enough. Is there another side?"),
    ("BUCKY", "Thanks, Chip! There always is. Here's what nobody at this table says out loud. Retail sales? Up more than six percent from a year ago! Unemployment? About four percent. The S and P five hundred sits near seventy-seven hundred! The economy keeps building while Washington keeps arguing. Builders build, Chip. That's what we do!"),
    ("DUHBURRO", "The Burro said it first, Bucky! Thanks to us!"),
    ("DUHELEFANTE", "Old Righty said it first, Bucky. Thanks to us."),
    ("BITME", "Touching. This bear has seen the movie. Two parties. One talking point. Bucky builds it, and they both take the credit."),
    # 6. The midterms
    ("HOST", "Which brings us to question six. The midterms. And the date I promised you at the top of the show. Hooter. You've been holding it."),
    ("HOOTER", "I have. Mark it well. October's inflation report arrives November tenth. One week after the votes are counted. The voters decide first. The facts arrive second. Caveat emptor."),
    ("HOST", "That got quiet. Burro? Elephant? Anything?"),
    ("DUHBURRO", "Can the Burro move the election?"),
    ("DUHELEFANTE", "Can Old Righty move the report?"),
    ("HOST", "No. You can't. Bad Ask. We started with who did it. The last question goes to you."),
    ("BADASK", "Who really sets the price of a gallon of diesel? A mortgage? A Treasury bond? The voters on November third? Or Da Cabal, every morning at eight?"),
    ("CAPO", "Eight sharp. Capo is never late."),
    ("HOST", "And that's our roundtable. The microphones go dark. And the Duhs clink coffee cups."),
    ("DUHBURRO", "Same time after the election, Old Righty?"),
    ("DUHELEFANTE", "Same trough, Old Lefty."),
]
HOST_LINES = [t for w, t in LINES if w == "HOST"]


def run(*args):
    return subprocess.run([FF, "-y", "-loglevel", "error", *map(str, args)], check=True, capture_output=True, text=True)


def to_wav(src, dst, ss=None, to=None):
    cut = (["-ss", f"{ss:.3f}"] if ss is not None else []) + (["-to", f"{to:.3f}"] if to is not None else [])
    run(*cut, "-i", src, "-ar", "44100", "-ac", "1", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", dst)


def silence(sec, dst):
    run("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", sec, dst)


VENV_PY = r"C:\Users\Chip\Tools\voiceclone_venv\Scripts\python.exe"
OUTRO_TXT = BUCKY / "Host outro VOICE v2 - Duhs at the Roundtable 2026-10-25.txt"


def reference_clip():
    """About 15 seconds of Chip's intro, cut at pauses, as the cloning reference."""
    src = BUCKY / "host intro.mp3"
    p = subprocess.run([FF, "-i", str(src), "-af", "silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True)
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    a = min(ends, key=lambda t: abs(t - 4))
    b = min([s for s in starts if s > a + 10], key=lambda t: abs(t - (a + 15)))
    ref = WORK / "chip_reference.wav"
    run("-ss", f"{a - 0.05:.2f}", "-to", f"{b + 0.05:.2f}", "-i", src, "-ar", "24000", "-ac", "1", ref)
    print(f"reference {a:.1f}s to {b:.1f}s")
    return ref


def clone_host():
    """Voice every HOST line and each outro paragraph in Chip's cloned voice."""
    outro = [" ".join(p.split("\n")) for p in OUTRO_TXT.read_text(encoding="utf-8").strip().split("\n\n")]
    jobs = [{"text": t, "out": str(WORK / f"host_{i:02d}_raw.wav")} for i, t in enumerate(HOST_LINES, 1)]
    jobs += [{"text": t, "out": str(WORK / f"outro_{i:02d}_raw.wav")} for i, t in enumerate(outro, 1)]
    (WORK / "host_jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
    subprocess.run([VENV_PY, str(Path(__file__).parent / "clone_host.py"), str(reference_clip()),
                    str(WORK / "host_jobs.json")], check=True)
    for j in jobs:
        to_wav(j["out"], j["out"].replace("_raw", ""))
    silence(0.6, WORK / "gap_para.wav")
    parts = []
    for i in range(1, len(outro) + 1):
        parts += [WORK / f"outro_{i:02d}.wav", WORK / "gap_para.wav"]
    concat(parts[:-1], WORK / "outro.mp3")
    to_wav(WORK / "outro.mp3", WORK / "outro.wav")

async def tts(text, voice, rate, pitch, mp3):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(mp3))


def concat(parts, out):
    lst = WORK / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run("-f", "concat", "-safe", "0", "-i", lst, "-codec:a", "libmp3lame", "-b:a", "128k", out)


def audition():
    silence(0.5, WORK / "gap.wav")
    silence(1.2, WORK / "gap_long.wav")
    parts = []
    for who, cands in CANDIDATES.items():
        for n, (voice, rate, pitch) in enumerate(cands, 1):
            tag, line = WORK / f"aud_{who}_{n}_tag.mp3", WORK / f"aud_{who}_{n}.mp3"
            asyncio.run(tts(f"{LABEL[who]}. Option {n}.", "en-US-JennyNeural", "+0%", "+0Hz", tag))
            asyncio.run(tts(SAMPLES[who], voice, rate, pitch, line))
            for f in (tag, line):
                to_wav(f, f.with_suffix(".wav"))
            parts += [tag.with_suffix(".wav"), WORK / "gap.wav", line.with_suffix(".wav"), WORK / "gap_long.wav"]
    concat(parts, REEL)
    print(REEL)


def main():
    clone_host()
    silence(1.0, WORK / "gap_long.wav")
    silence(0.4, WORK / "gap.wav")
    to_wav(BUCKY / "host intro.mp3", WORK / "intro.wav")
    parts, h = [WORK / "intro.wav", WORK / "gap_long.wav"], 0
    for i, (who, text) in enumerate(LINES, 1):
        if who == "HOST":
            h += 1
            wav = WORK / f"host_{h:02d}.wav"
        else:
            voice, rate, pitch = CANDIDATES[who][PICK[who]]
            mp3 = WORK / f"{i:02d}_{who}.mp3"
            asyncio.run(tts(text, voice, rate, pitch, mp3))
            wav = mp3.with_suffix(".wav")
            to_wav(mp3, wav)
        parts += [wav, WORK / "gap.wav"]
    parts[-1] = WORK / "gap_long.wav"
    parts.append(WORK / "outro.wav")
    concat(parts, OUT)
    print(OUT)


if __name__ == "__main__":
    audition() if sys.argv[1:] == ["audition"] else main()
