"""Build a multi-voice Bullchip Banter episode: host intro + roundtable + host outro.

python assets/banter/build_episode.py
Character lines are voiced with Microsoft neural voices (edge-tts); Chip's host
intro and outro come from his NaturalReader exports. Output: one loudness-matched MP3.
"""
import asyncio
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

BUCKY = Path(r"\\SERVER01\Folder Redirection\Chip\Documents\1 SUBSTACK\Bucky DaBull")
WORK = Path(__file__).parent / "_episode_work"
WORK.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = BUCKY / "Bullchip Banter - Duhs at the Roundtable EPISODE 2026-10-25.mp3"

# voice, rate, pitch
CAST = {
    "DUHBURRO": ("en-US-ChristopherNeural", "+12%", "+0Hz"),   # fast-talking
    "DUHELEFANTE": ("en-US-GuyNeural", "-12%", "-6Hz"),        # slow, deep
    "BUCKY": ("en-US-AndrewNeural", "+4%", "-2Hz"),            # confident baritone
    "BITME": ("en-US-RogerNeural", "-6%", "-8Hz"),             # gruff, gloomy
    "HOOTER": ("en-GB-ThomasNeural", "-8%", "-2Hz"),           # older British
    "BADASK": ("en-AU-WilliamMultilingualNeural", "+8%", "+0Hz"),  # quick doer
    "BOSSHOG": ("en-US-EricNeural", "-5%", "-10Hz"),           # big, booming
    "CAPO": ("it-IT-GiuseppeMultilingualNeural", "-4%", "-2Hz"),   # Italian accent
    "LEPHEWY": ("fr-FR-RemyMultilingualNeural", "-2%", "+2Hz"),    # French accent
    "NARRATOR": ("en-US-BrianNeural", "-4%", "+0Hz"),          # stage directions
}

# Spoken script: rounded numbers, voice-safe names, no heteronyms.
LINES = [
    ("NARRATOR", "Duh Burro, the donkey, taps the microphone."),
    ("DUHBURRO", "Is this thing on? Good. Folks, prices are up nearly four percent from a year ago. Who did that? Not us."),
    ("NARRATOR", "Duh Ella-fahn-tay, the elephant, bangs his gavel."),
    ("DUHELEFANTE", "Not us either, Burro. Put it in writing. We were out of the room."),
    ("NARRATOR", "Hooter the owl checks his notebook."),
    ("HOOTER", "The data show prices rose more than half a percent in September alone. Gasoline was the biggest push. Core inflation, without food and energy, is under three percent."),
    ("DUHBURRO", "Core? Nobody eats core. Nobody drives core."),
    ("DUHELEFANTE", "For once, my donkey friend is right. Strike that. Pretend I never said it."),
    ("NARRATOR", "Bad Ask the badger leans in."),
    ("BADASK", "Diesel is over six dollars a gallon. A year ago it was under four. That's up nearly three quarters. Every truck, tractor and freight train burns it. So who pays?"),
    ("DUHBURRO", "The consumer pays. Which is why we're blaming the elephant's side."),
    ("DUHELEFANTE", "And we're blaming the donkey's side. See? Bipartisan."),
    ("NARRATOR", "Bit Me Da Bear grumbles from his chair."),
    ("BITME", "Brent crude is about a hundred and fifteen dollars a barrel. A year ago, about sixty. Earlier this month it touched a hundred and thirty. The Iran war began in February. Do you think diesel cares who's in charge?"),
    ("DUHBURRO", "Then we need lower interest rates. Before November third."),
    ("DUHELEFANTE", "Seconded. All in favor? Unanimous."),
    ("NARRATOR", "At the far end of the table, Capo Da Wolf doesn't look up."),
    ("CAPO", "You vote. We price. The Fed holds the short rate near four percent. The ten-year Treasury pays more than five. That one is ours."),
    ("DUHBURRO", "Who elected you, wolf?"),
    ("CAPO", "Nobody. That's why we're still here. Mortgages cost more than seven percent. The federal debt is nearly forty trillion dollars. The interest bill tops a trillion dollars a year. More than defense."),
    ("DUHELEFANTE", "A trillion for interest? Who borrowed all that?"),
    ("NARRATOR", "The donkey points at the elephant. The elephant points right back."),
    ("HOOTER", "Hooter here. The ledger says both."),
    ("NARRATOR", "Boss Hog grins."),
    ("BOSSHOG", "Don't stop now, fellas. Nine days to go. Who's handing out the checks?"),
    ("DUHBURRO", "A diesel rebate!"),
    ("DUHELEFANTE", "A gas tax holiday!"),
    ("CAPO", "Paid for with what, gentlemen? More bonds? Yours."),
    ("NARRATOR", "Le Phooey the polecat slides into an empty chair."),
    ("LEPHEWY", "Gentlemen. I have a coin that hedges inflation, diesel, and elections. Guaranteed."),
    ("BADASK", "Bitcoin is about eighty-two thousand dollars, Le Phooey. A year ago it was about a hundred and seven thousand. Some hedge."),
    ("LEPHEWY", "Past performance..."),
    ("NARRATOR", "And the polecat is gone."),
    ("NARRATOR", "Bucky Da Bull clears his throat."),
    ("BUCKY", "Here's what nobody at this table says out loud. Retail sales are up more than six percent from a year ago. Unemployment is about four percent. The S and P five hundred sits near seventy-seven hundred. The economy keeps building while Washington argues."),
    ("DUHBURRO", "Exactly what I said, Bucky. Thanks to us."),
    ("DUHELEFANTE", "Exactly what I said, Bucky. Thanks to us."),
    ("NARRATOR", "Hooter taps his notebook."),
    ("HOOTER", "One more date. October's inflation report comes out November tenth. One week after the votes are counted."),
    ("NARRATOR", "A long pause."),
    ("DUHBURRO", "Can we move the election?"),
    ("DUHELEFANTE", "Can we move the report?"),
    ("NARRATOR", "Bad Ask asks the last question."),
    ("BADASK", "So who really sets the price of a gallon of diesel, a mortgage, a Treasury bond? The voters on November third? Or Da Cabal, every morning at eight?"),
    ("NARRATOR", "Off mic, the Duhs clink coffee cups."),
    ("DUHBURRO", "Same time after the election?"),
    ("DUHELEFANTE", "Same trough."),
]


async def voice_all():
    for i, (who, text) in enumerate(LINES, 1):
        voice, rate, pitch = CAST[who]
        mp3 = WORK / f"{i:02d}_{who}.mp3"
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(mp3))


def to_wav(src, dst):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "1",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", str(dst)], check=True)


def silence(sec, dst):
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(sec), str(dst)], check=True)


def main():
    asyncio.run(voice_all())
    parts = []
    to_wav(BUCKY / "host intro.mp3", WORK / "intro.wav")
    parts += [WORK / "intro.wav"]
    silence(1.2, WORK / "gap_long.wav")
    silence(0.45, WORK / "gap.wav")
    silence(0.75, WORK / "gap_narr.wav")
    parts.append(WORK / "gap_long.wav")
    prev = None
    for i, (who, _) in enumerate(LINES, 1):
        wav = WORK / f"{i:02d}_{who}.wav"
        to_wav(WORK / f"{i:02d}_{who}.mp3", wav)
        if prev is not None:
            parts.append(WORK / ("gap_narr.wav" if "NARRATOR" in (who, prev) else "gap.wav"))
        parts.append(wav)
        prev = who
    parts.append(WORK / "gap_long.wav")
    to_wav(BUCKY / "host outro.mp3", WORK / "outro.wav")
    parts.append(WORK / "outro.wav")
    lst = WORK / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-codec:a", "libmp3lame", "-b:a", "128k", str(OUT)], check=True)
    print(OUT)


if __name__ == "__main__":
    main()
