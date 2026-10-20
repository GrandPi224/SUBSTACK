"""Bucky's Blokes: the 19-point market checklist.

Fetches every series in checklist.json from FRED, draws one chart per item with a
centered red Chip Quip, and writes charts/*.png, stats.json, index.html and
buckys-blokes.pdf. Run by .github/workflows/buckys-blokes.yml (FRED blocks
direct downloads from Chip's PC, so the build runs on GitHub).

Local test without network:  python build.py --fake
"""
import io, json, sys, time, datetime as dt, html
from pathlib import Path
import numpy as np, pandas as pd, requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from matplotlib.backends.backend_pdf import PdfPages

HERE = Path(__file__).parent
CFG = json.loads((HERE / "checklist.json").read_text(encoding="utf-8"))
FAKE = "--fake" in sys.argv
NAVY, TEAL, GOLD, RED, GRAY = "#1F3864", "#0ABAB5", "#C9A227", "#C00000", "#595959"
COLORS = [NAVY, TEAL, GOLD]
FS = 14
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS})
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def fred(sid):
    if FAKE:
        idx = pd.date_range("2000-01-01", "2026-09-01", freq="MS")
        return pd.Series(np.abs(np.cumsum(np.random.randn(len(idx)))) + 2, idx)
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            df = pd.read_csv(io.StringIO(r.text))
            s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            s.index = pd.to_datetime(df.iloc[:, 0])
            return s.dropna()
        except Exception as e:
            print(sid, "attempt", attempt + 1, e)
            time.sleep(3)
    raise RuntimeError(f"FRED fetch failed for {sid}")


_cache = {}
def get(sid):
    if sid not in _cache:
        _cache[sid] = fred(sid)
    return _cache[sid]


def load(spec, item):
    if "spread" in spec:
        a, b = (get(x).resample("MS").mean() for x in spec["spread"])
        s = (a - b).dropna()
    else:
        s = get(spec["id"]) * spec.get("scale", 1)
    daily = len(s) > 2 and (s.index[1] - s.index[0]).days < 7
    if daily:
        s = s.resample("W-FRI").last().dropna() if item.get("log") or item["start"] >= "2016" else s.resample("MS").mean()
    if item["transform"] == "yoy":
        s = (s / s.shift(freq=pd.DateOffset(years=1)).reindex(s.index) - 1) * 100
    return s[s.index >= item["start"]].dropna()


def fmt(v, item):
    u = item["unit"]
    num = f"{v:,.1f}"
    if item.get("prefix"):
        return "$" + num + ("" if u == "$" else " " + {"B": "billion", "T": "trillion"}.get(u, u))
    u = {"K": "thousand"}.get(u.strip(), u)
    return num + (u if u in ("%",) else (" " + u.strip() if u.strip() else ""))


def stats(s):
    last, ld = float(s.iloc[-1]), s.index[-1]
    prior = s[s.index <= ld - pd.DateOffset(years=1)]
    yago = float(prior.iloc[-1]) if len(prior) else float("nan")
    hist = s.iloc[:-1]
    higher = hist[hist >= last]
    lower = hist[hist <= last]
    if len(higher) == 0:
        extreme = "a record high on this chart"
    elif len(lower) == 0:
        extreme = "a record low on this chart"
    elif higher.index[-1] < lower.index[-1]:
        extreme = f"the highest since {MONTHS[higher.index[-1].month - 1]} {higher.index[-1].year}"
    else:
        extreme = f"the lowest since {MONTHS[lower.index[-1].month - 1]} {lower.index[-1].year}"
    return dict(last=last, date=ld.strftime("%Y-%m-%d"), mon=f"{MONTHS[ld.month - 1]} {ld.year}",
                yago=yago, extreme=extreme, hi=float(s.max()), lo=float(s.min()))


def quip(item, st):
    lab = item["series"][0]["label"]
    yoy = " y/y" if item["transform"] == "yoy" else ""
    line1 = f"{lab}: {fmt(st['last'], item)}{yoy} in {st['mon']}, {st['extreme']}."
    return line1, item["question"]


def recessions():
    r = get("USREC")
    r = r[r.index >= "1999-01-01"]
    out, start = [], None
    for d, v in r.items():
        if v == 1 and start is None: start = d
        if v == 0 and start is not None: out.append((start, d)); start = None
    if start is not None: out.append((start, r.index[-1]))
    return out


def chart(item, data, st, recs):
    fig = plt.figure(figsize=(12, 7.6), facecolor="white")
    ax = fig.add_axes([0.08, 0.2, 0.88, 0.58])
    for a, b in recs:
        if b >= data[0].index[0]:
            ax.axvspan(max(a, data[0].index[0]), b, color="#D9D9D9", lw=0, zorder=0)
    for i, (spec, s) in enumerate(zip(item["series"], data)):
        ax.plot(s.index, s.values, color=COLORS[i], lw=2.6 if i == 0 else 2.0, label=spec["label"], zorder=3)
        if spec.get("ma"):
            ax.plot(s.index, s.rolling(spec["ma"]).mean(), color=RED, lw=1.6, label=f"{spec['ma']}-week average", zorder=2)
    if item.get("log"):
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_minor_formatter(mt.NullFormatter())
    else:
        ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.1f}" if abs(v) < 20 else f"{v:,.0f}"))
    if item["transform"] == "yoy" or any("spread" in s for s in item["series"]):
        ax.axhline(0, color=GRAY, lw=1)
    lv = data[0].iloc[-1]
    ax.annotate(fmt(lv, item), (data[0].index[-1], lv), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=FS, fontweight="bold", color=COLORS[0])
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color("#BFBFBF")
    ax.tick_params(labelsize=FS, colors="#404040")
    ax.grid(axis="y", color="#E5E5E5", lw=0.8)
    ax.set_xlim(data[0].index[0], data[0].index[-1] + pd.Timedelta(days=(data[0].index[-1] - data[0].index[0]).days * 0.08))
    if len(item["series"]) > 1 or any(s.get("ma") for s in item["series"]):
        ax.legend(loc="upper left", fontsize=FS, frameon=False)
    fig.text(0.08, 0.95, f"BUCKY'S BLOKES  |  {item['n']:02d}  |  {item['bloke'].upper()}: {item['read'].upper()}",
             fontsize=FS, color=TEAL, fontweight="bold")
    fig.text(0.08, 0.895, item["heading"], fontsize=24, fontweight="bold", color=NAVY)
    fig.text(0.08, 0.85, item["subtitle"] + ". Shaded: US recessions.", fontsize=FS, color=GRAY)
    l1, l2 = quip(item, st)
    fig.text(0.5, 0.105, f"Chip Quip: {l1}", ha="center", fontsize=FS if len(l1) < 90 else FS - 1.5, color=RED, style="italic")
    fig.text(0.5, 0.065, l2, ha="center", fontsize=FS, color=RED, style="italic")
    ids = ", ".join(sorted({x for sp in item["series"] for x in sp.get("spread", [sp["id"]])}))
    fig.text(0.08, 0.018, f"Source: FRED, Federal Reserve Bank of St. Louis ({ids}). Data through {st['mon']}.",
             fontsize=11, color=NAVY, style="italic")
    return fig


def main():
    recs = recessions()
    out, figs = [], []
    (HERE / "charts").mkdir(exist_ok=True)
    pdf = PdfPages(HERE / "buckys-blokes.pdf")
    cover = plt.figure(figsize=(12, 7.6))
    cover.text(0.5, 0.6, CFG["title"], ha="center", fontsize=40, fontweight="bold", color=NAVY)
    cover.text(0.5, 0.5, CFG["subtitle"], ha="center", fontsize=20, color=GRAY)
    cover.text(0.5, 0.4, f"Built {dt.date.today():%B %d, %Y}. Source: FRED, Federal Reserve Bank of St. Louis.",
               ha="center", fontsize=FS, color=GRAY)
    cover.text(0.5, 0.3, "The bull builds. The bear bellyaches. The owl benchmarks.", ha="center", fontsize=FS, color=TEAL, style="italic")
    pdf.savefig(cover); plt.close(cover)
    for item in CFG["items"]:
        data = [load(sp, item) for sp in item["series"]]
        sts = [stats(s) for s in data]
        st = sts[0]
        fig = chart(item, data, st, recs)
        png = f"charts/{item['n']:02d}-{item['slug']}.png"
        fig.savefig(HERE / png, dpi=150, facecolor="white")
        pdf.savefig(fig); plt.close(fig)
        tokens = {"last": f"{st['last']:,.1f}", "yago": f"{st['yago']:,.1f}", "mon": st["mon"]}
        if len(sts) > 1: tokens["last2"] = f"{sts[1]['last']:,.1f}"
        status = item["status"].format(**tokens)
        l1, l2 = quip(item, st)
        out.append(dict(n=item["n"], slug=item["slug"], heading=item["heading"], bloke=item["bloke"], read=item["read"],
                        status=status, quip1=l1, quip2=l2, png=png, stats=sts))
        print(f"{item['n']:2d} {item['heading']}: {l1}")
    pdf.close()
    (HERE / "stats.json").write_text(json.dumps(dict(built=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), items=out), indent=1), encoding="utf-8")
    write_html(out)


def write_html(out):
    e = html.escape
    rows = []
    for o in out:
        rows.append(f"""<details class="item" id="{o['slug']}">
<summary><span class="num">{o['n']:02d}</span> {e(o['heading'])} <span class="read read-{o['read'].lower()}">{e(o['read'])}</span></summary>
<p class="kicker">{e(o['bloke'])}'s read: {e(o['read'])}</p>
<p>{e(o['status'])}</p>
<img src="{o['png']}?v={dt.date.today():%Y%m%d}" alt="{e(o['heading'])} chart. {e(o['quip1'])}" loading="lazy" width="1800" height="1140">
<p class="quip">Chip Quip: {e(o['quip1'])}<br>{e(o['quip2'])}</p>
</details>""")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bucky's Blokes: The Checklist</title>
<meta name="description" content="{e(CFG['subtitle'])}">
<link rel="stylesheet" href="../assets/site.css?v=5">
<style>
details.item summary{{font-size:1.15em;font-weight:700;cursor:pointer;padding:.5em 0}}
.num{{display:inline-block;min-width:2.2em;color:#0ABAB5}}
.read{{font-size:.8em;padding:.1em .5em;border-radius:4px;margin-left:.5em}}
.read-positive{{background:#E2F5EC;color:#14532D}} .read-neutral{{background:#EEF0F4;color:#1F3864}} .read-negative{{background:#FBE4E4;color:#7F1D1D}}
details.item img{{width:100%;height:auto;border:1px solid #ddd}}
.quip{{color:#C00000;font-style:italic;text-align:center}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header>
  <p class="kicker"><a href="../">Sources and Notes</a> · <a href="../cast/">The Cast</a></p>
  <h1>Bucky's Blokes</h1>
  <p class="lead">{e(CFG['subtitle'])}. Each item: a status, a read from one of the blokes, and a chart with a Chip Quip. <a href="buckys-blokes.pdf">Download the PDF</a>.</p>
</header>
<main id="main">
{chr(10).join(rows)}
<p class="kicker">Built {dt.date.today():%B %d, %Y} from FRED, Federal Reserve Bank of St. Louis. Questions and observations, not advice.</p>
</main>
</body>
</html>
"""
    (HERE / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
