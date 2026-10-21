"""Build one page per character from cast/index.html.

cast/index.html is the master. Edit it, then run:  python cast/build_pages.py
Writes cast/<id>/index.html for every <article class="bloke"> and <section class="cabal">.
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
src = (HERE / "index.html").read_text(encoding="utf-8")

css = re.search(r'<link rel="stylesheet" href="\.\./assets/site\.css\?v=(\d+)">', src).group(1)
footer = re.search(r"<footer>.*?</footer>", src, re.S).group(0)
blocks = re.findall(r'(    <(article|section) class="(?:bloke|cabal)" id="([^"]+)".*?</\2>)', src, re.S)


def name_of(html):
    return re.sub(r"<[^>]+>", "", re.search(r"<h2[^>]*>(.*?)</h2>", html, re.S).group(1)).strip()


cast = [(bid, name_of(html), html) for html, _, bid in blocks]

for i, (bid, name, html) in enumerate(cast):
    body = html.replace('src="../assets/', 'src="../../assets/')
    prev_id, prev_name = cast[i - 1][0], cast[i - 1][1]
    next_id, next_name = cast[(i + 1) % len(cast)][0], cast[(i + 1) % len(cast)][1]
    others = "\n".join(
        f'    <li><a href="../{oid}/">{oname}</a></li>' for oid, oname, _ in cast if oid != bid
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}: Bucky's Blokes</title>
<meta name="description" content="Meet {name}, one of Bucky's Blokes, the Wall Street cast of characters in William &quot;Chip&quot; Corley's Substack.">
<link rel="stylesheet" href="../../assets/site.css?v={css}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header>
  <p class="kicker"><a href="../">Bucky's Blokes: the whole cast</a></p>
</header>
<main id="main">
{body}
  <nav class="cast-nav" aria-label="More of the cast">
    <p><a href="../{prev_id}/">&larr; {prev_name}</a> · <a href="../{next_id}/">{next_name} &rarr;</a></p>
    <h2>Meet the rest of the blokes</h2>
    <ul>
{others}
    </ul>
  </nav>
</main>
{footer}
</body>
</html>
"""
    out = HERE / bid / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(out.relative_to(HERE.parent))
