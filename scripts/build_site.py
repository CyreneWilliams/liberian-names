"""Rebuild the site from data/names.json and src/template.html.

Usage (from the repository folder):  python3 scripts/build_site.py

Writes:
  index.html            the archive itself (template + embedded data)
  names/index.html      an A-Z list of every name, readable without JavaScript
  names/<id>/index.html one page per name, so search engines can find each name
  404.html              a real "not found" page (without it, Cloudflare serves the home page)
  sitemap.xml, robots.txt
  _headers              security headers, including a Content-Security-Policy that
                        allows the archive's own inline script by its hash
"""
import base64
import datetime
import hashlib
import html
import json
import os
import re
import shutil
from collections import defaultdict

SITE = "https://liberiannames.com"
SUPABASE = "https://rgqagbxxygrouhdklhva.supabase.co"
FOUNDERS = ["Cyrene Williams", "Winifred Gray-Johnson"]
DESC = ("An open, community-built archive of Liberian traditional names: meanings, tribes, "
        "spellings and the people who shared them.")

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
today = datetime.date.today().isoformat()
year = datetime.date.today().year


def path(*p):
    return os.path.join(root, *p)


def write(rel, text):
    full = path(*rel.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def esc(s):
    return html.escape(str(s), quote=True)


def ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


with open(path("data", "names.json"), encoding="utf-8") as f:
    d = json.load(f)

# ---------- index.html (the archive) ----------
G = {"Female": "F", "Male": "M", "Unisex": "U", "Unknown": ""}
INFERRED = "Gender inferred from the meaning."
names = [e for e in d["names"] if not e["surname"]]
out = [
    [
        e["name"],
        e["variants"],
        G[e["gender"]],
        e["tribes"],
        [[m["text"], m["tribes"], m["count"], m.get("source", "")] for m in e["meanings"]],
        e["pronunciation"],
        [n for n in e["notes"] if n != INFERRED],
        e["submissions"],
        int("Tribe marked uncertain" in e["issues"]),
        [[x["title"].split(",")[0], x["url"]] for x in e.get("sources", [])],
    ]
    for e in names
]
surnames = [e["name"] for e in d["names"] if e["surname"]]
data = json.dumps({"n": out, "s": surnames}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
tribe_count = len({t for e in names for t in e["tribes"]})

site_ld = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebSite", "@id": SITE + "/#website", "name": "Liberian Names", "url": SITE + "/",
         "description": DESC, "inLanguage": "en",
         "publisher": {"@id": SITE + "/#project"}},
        {"@type": "Organization", "@id": SITE + "/#project", "name": "Liberian Names", "url": SITE + "/",
         "logo": SITE + "/assets/social-card.png",
         "founder": [{"@type": "Person", "name": n} for n in FOUNDERS]},
        {"@type": "Dataset", "@id": SITE + "/#dataset",
         "name": "Liberian Names: an archive of Liberian traditional names",
         "description": (f"A community-built record of {len(names)} Liberian traditional names across "
                         f"{tribe_count} ethnic groups, with meanings, spellings, pronunciations, birth-order "
                         "names and the number of people who shared each meaning. Collection began in 2020; "
                         "every contribution is reviewed by an editor before it is published."),
         "url": SITE + "/", "keywords": ["Liberia", "names", "onomastics", "Kpelle", "Bassa", "Kru",
                                         "Grebo", "Vai", "Lorma", "cultural heritage", "oral tradition"],
         "spatialCoverage": {"@type": "Place", "name": "Liberia"},
         "temporalCoverage": "2020/..", "inLanguage": "en", "isAccessibleForFree": True,
         "creator": [{"@type": "Person", "name": n} for n in FOUNDERS],
         "dateModified": today},
    ],
}

with open(path("src", "template.html"), encoding="utf-8") as f:
    template = f.read()
for ph in ("__DATA__", "__JSONLD__"):
    assert template.count(ph) == 1, f"template.html must contain {ph} exactly once"
index_html = template.replace("__JSONLD__", ld(site_ld)).replace("__DATA__", data)
write("index.html", index_html)

# ---------- shared page shell for the static pages ----------
CSS = """
:root{--bg:#F7F8FB;--surface:#fff;--ink:#0F1730;--muted:#566079;--line:#DDE2EE;--blue:#002868;--blue-soft:#E4EAF5;--red:#BF0A30;
--display:"Young Serif",Georgia,serif;--body:"Instrument Sans","Segoe UI",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0A1022;--surface:#121A33;--ink:#EDF0F8;--muted:#A3ABC6;--line:#26304F;--blue:#8EA9EE;--blue-soft:#18264D;--red:#F2475F;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 var(--body)}
a{color:var(--blue)}.wrap{max-width:760px;margin:0 auto;padding:0 16px}
.ribbon{height:6px;background:repeating-linear-gradient(180deg,#BF0A30 0 1px,#fff 1px 2px)}
header{padding:18px 0;border-bottom:1px solid var(--line)}header a{font-family:var(--display);font-size:22px;text-decoration:none;color:var(--ink)}
.crumbs{font-size:14px;color:var(--muted);margin:20px 0 0}.crumbs a{color:var(--muted)}
h1{font-family:var(--display);font-weight:400;font-size:clamp(40px,9vw,64px);line-height:1.05;margin:8px 0 6px;overflow-wrap:anywhere}
h2{font-family:var(--display);font-weight:400;font-size:22px;margin:32px 0 8px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px;padding:0;list-style:none}
.tags li{background:var(--blue-soft);color:var(--blue);border-radius:99px;padding:2px 12px;font-size:14px;font-weight:600}
.meanings{padding:0;list-style:none;margin:0}.meanings li{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 10px;font-size:20px}
.meanings small{display:block;color:var(--muted);font-size:14px}
.pron{font-family:var(--mono)}.note{color:var(--muted)}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin:28px 0}
.btn{display:inline-block;padding:10px 18px;border-radius:99px;background:var(--blue);color:#fff;text-decoration:none;font-weight:600}
@media (prefers-color-scheme:dark){.btn{color:#0A1022}}
.btn.alt{background:transparent;color:var(--blue);border:1.5px solid var(--blue)}
.related{display:flex;flex-wrap:wrap;gap:6px 14px;padding:0;list-style:none}
.cite{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--red);border-radius:6px;padding:12px 16px;font-size:15px;overflow-wrap:anywhere}
.az h2{border-bottom:1px solid var(--line);padding-bottom:4px}.az ul{list-style:none;padding:0;margin:0;columns:2 220px}
.az li{break-inside:avoid;margin:0 0 6px}.az small{color:var(--muted)}
.letters{display:flex;flex-wrap:wrap;gap:4px 10px;font-family:var(--mono)}
footer{margin:48px 0 0;padding:24px 0 40px;border-top:1px solid var(--line);color:var(--muted);font-size:14px}
"""
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Instrument+Sans:wght@400;600&family=IBM+Plex+Mono&display=swap">')
ICON = re.search(r'<link rel="icon"[^>]*>', template).group(0)


def page(title, desc, url, body, jsonld=None, robots=None):
    meta_robots = f'<meta name="robots" content="{robots}">' if robots else ""
    canon = f'<link rel="canonical" href="{url}"><meta property="og:url" content="{url}">' if url else ""
    j = f'<script type="application/ld+json">{ld(jsonld)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{meta_robots}{canon}
<meta property="og:site_name" content="Liberian Names"><meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/assets/social-card.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#002868">
{ICON}
{FONTS}
<style>{CSS}</style>
{j}
</head>
<body>
<div class="ribbon" aria-hidden="true"></div>
<header><div class="wrap"><a href="/">Liberian Names</a></div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">Liberian Names · an open community archive, started 2020. Every meaning is reviewed before it appears.<br>
A project by Cyrene Williams and Winifred Gray-Johnson, co-founders and contributors</div></footer>
</body>
</html>
"""


GENDER_WORD = {"Female": "girl's name", "Male": "boy's name", "Unisex": "name for a girl or boy", "Unknown": "name"}
GENDER_TAG = {"Female": "Girl", "Male": "Boy", "Unisex": "Girl or boy", "Unknown": ""}


def tribe_phrase(e):
    t = e["tribes"]
    if not t:
        return ""
    return " and ".join([", ".join(t[:-1]), t[-1]]) if len(t) > 1 else t[0]


def describe(e):
    """One-sentence summary used for titles and meta descriptions."""
    tp = tribe_phrase(e)
    who = f"{'an' if tp[:1] in 'AEIOU' and tp else 'a'} {tp + ' ' if tp else 'Liberian '}{GENDER_WORD[e['gender']]}"
    if e["meanings"]:
        return f"{e['name']} is {who} meaning “{e['meanings'][0]['text']}”."
    return f"{e['name']} is {who}. Its meaning hasn't been recorded yet."


def slug_url(e):
    return f"{SITE}/names/{e['id']}/"


by_tribe = defaultdict(list)
for e in names:
    for t in e["tribes"]:
        by_tribe[t].append(e)

# Clear previously generated name pages so removed names don't linger.
if os.path.isdir(path("names")):
    shutil.rmtree(path("names"))

for e in names:
    url = slug_url(e)
    tp = tribe_phrase(e)
    m0 = e["meanings"][0]["text"] if e["meanings"] else ""
    title = (f"{e['name']}: {tp + ' ' if tp else 'Liberian '}name meaning “{m0}” · Liberian Names" if m0
             else f"{e['name']}: {tp + ' ' if tp else 'Liberian '}name · Liberian Names")
    desc = describe(e) + " Meanings, spellings, tribe and pronunciation in the open Liberian Names archive."

    tags = [t for t in [GENDER_TAG[e["gender"]]] + e["tribes"] if t]
    parts = [f'<p class="crumbs"><a href="/">Home</a> › <a href="/names/">All names</a> › {esc(e["name"])}</p>',
             f"<h1>{esc(e['name'])}</h1>"]
    if tags:
        parts.append('<ul class="tags">' + "".join(f"<li>{esc(t)}</li>" for t in tags) + "</ul>")
    parts.append(f"<p>{esc(describe(e))}</p>")

    parts.append("<h2>Meaning</h2>")
    if e["meanings"]:
        lis = []
        for m in e["meanings"]:
            by = (f"Shared by {m['count']} {'person' if m['count'] == 1 else 'people'}" if m["count"]
                  else f"From {m.get('source') or 'a published source'}")
            if len(e["tribes"]) > 1 and m["tribes"]:
                by += " · " + ", ".join(m["tribes"])
            lis.append(f"<li>{esc(m['text'])}<small>{esc(by)}</small></li>")
        parts.append('<ul class="meanings">' + "".join(lis) + "</ul>")
    else:
        parts.append('<p class="note">No meaning has been recorded yet. If you know it, please add it to the archive.</p>')
    if e["variants"]:
        parts.append("<h2>Other spellings</h2><p>" + ", ".join(esc(v) for v in e["variants"]) + "</p>")
    if e["pronunciation"]:
        parts.append('<h2>Pronunciation</h2><p class="pron">' + " · ".join(esc(p) for p in e["pronunciation"]) + "</p>")
    notes = [n for n in e["notes"] if n != INFERRED]
    if notes:
        parts.append("<h2>Notes</h2>" + "".join(f"<p>{esc(n)}</p>" for n in notes))
    if "Tribe marked uncertain" in e["issues"]:
        parts.append('<p class="note">The tribe for this name is marked uncertain. Corrections are welcome.</p>')

    if e.get("sources"):
        parts.append("<h2>Sources</h2><p>" + "; ".join(
            f'<a href="{esc(x["url"])}" rel="nofollow noopener">{esc(x["title"])}</a> (accessed {esc(x["accessed"])})'
            for x in e["sources"]) + ". Published sources are listed until the community confirms the entry.</p>")
    parts.append(f'<div class="actions"><a class="btn" href="/#name={esc(e["id"])}">Open in the archive</a>'
                 '<a class="btn alt" href="/#contribute">Add a meaning, spelling or recording</a></div>')

    for t in e["tribes"][:2]:
        rel = [x for x in by_tribe[t] if x["id"] != e["id"]][:14]
        if rel:
            parts.append(f"<h2>More {esc(t)} names</h2><ul class=\"related\">" +
                         "".join(f'<li><a href="/names/{esc(x["id"])}/">{esc(x["name"])}</a></li>' for x in rel) + "</ul>")

    parts.append("<h2>Cite this entry</h2>"
                 f'<p class="cite">Williams, C., &amp; Gray-Johnson, W. (Eds.). ({year}). {esc(e["name"])}. '
                 f'In <i>Liberian Names: An open archive of Liberian traditional names</i>. {esc(url)}</p>')

    term = {"@context": "https://schema.org", "@graph": [
        {"@type": "DefinedTerm", "@id": url, "name": e["name"], "url": url,
         "description": "; ".join(m["text"] for m in e["meanings"]) or describe(e),
         "inDefinedTermSet": {"@type": "DefinedTermSet", "@id": SITE + "/#dataset", "name": "Liberian Names", "url": SITE + "/"},
         **({"alternateName": e["variants"]} if e["variants"] else {})},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Liberian Names", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "All names", "item": SITE + "/names/"},
            {"@type": "ListItem", "position": 3, "name": e["name"], "item": url}]}]}
    write(f"names/{e['id']}/index.html", page(title, desc, url, "\n".join(parts), term))

# ---------- names/index.html (A-Z) ----------
groups = defaultdict(list)
for e in sorted(names, key=lambda x: x["id"]):
    groups[e["id"][0].upper()].append(e)
az = ['<p class="crumbs"><a href="/">Home</a> › All names</p>', "<h1>All names</h1>",
      f"<p>Every name in the archive, A to Z: {len(names)} names from {tribe_count} tribes. "
      'Search, filter and listen on the <a href="/">archive home page</a>.</p>',
      '<nav class="letters" aria-label="Jump to letter">' + "".join(f'<a href="#{L}">{L}</a>' for L in groups) + "</nav>",
      '<div class="az">']
for L, lst in groups.items():
    az.append(f'<h2 id="{L}">{L}</h2><ul>' + "".join(
        f'<li><a href="/names/{esc(e["id"])}/">{esc(e["name"])}</a>'
        + (f' <small>{esc(e["meanings"][0]["text"])}</small>' if e["meanings"] else "") + "</li>" for e in lst) + "</ul>")
az.append("</div>")
write("names/index.html", page(f"All {len(names)} Liberian names, A to Z · Liberian Names",
                               f"Browse {len(names)} Liberian traditional names from {tribe_count} tribes, with meanings, A to Z.",
                               SITE + "/names/", "\n".join(az)))

# ---------- 404 ----------
write("404.html", page("Page not found · Liberian Names", "This page isn't in the archive.", None,
                       '<h1>Not found</h1><p>That page isn\'t in the archive. Try the <a href="/">home page</a> '
                       'or <a href="/names/">browse every name</a>.</p>', robots="noindex"))

# ---------- sitemap + robots ----------
urls = [SITE + "/", SITE + "/names/"] + [slug_url(e) for e in names]
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + "".join(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /src/\nDisallow: /scripts/\nDisallow: /supabase/\n\nSitemap: {SITE}/sitemap.xml\n")

# ---------- _headers (security) ----------
inline = [m.group(1) for m in re.finditer(r"<script>(.*?)</script>", index_html, re.S)]
hashes = " ".join("'sha256-%s'" % base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() for s in inline)
wss = SUPABASE.replace("https://", "wss://")
csp = "; ".join([
    "default-src 'self'",
    f"script-src 'self' {hashes}",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    f"img-src 'self' data: blob: {SUPABASE}",
    f"media-src 'self' blob: {SUPABASE}",
    f"connect-src 'self' {SUPABASE} {wss}",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests",
])
write("_headers", f"""# Generated by scripts/build_site.py. Edit the script, not this file.
/*
  Content-Security-Policy: {csp}
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Cross-Origin-Opener-Policy: same-origin
  Permissions-Policy: camera=(), geolocation=(), payment=(), usb=(), microphone=(self)

/src/*
  X-Robots-Tag: noindex
/scripts/*
  X-Robots-Tag: noindex
/supabase/*
  X-Robots-Tag: noindex

/assets/*
  Cache-Control: public, max-age=604800
""")

print(f"Built index.html with {len(out)} names and {len(surnames)} family names, "
      f"{len(names)} name pages, sitemap.xml ({len(urls)} URLs), robots.txt, 404.html and _headers")
