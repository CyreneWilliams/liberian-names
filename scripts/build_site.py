"""Rebuild index.html from data/names.json and src/template.html.

Usage (from the repository folder):  python3 scripts/build_site.py
"""
import json
import os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root, "data", "names.json"), encoding="utf-8") as f:
    d = json.load(f)

G = {"Female": "F", "Male": "M", "Unisex": "U", "Unknown": ""}
out = [
    [
        e["name"],
        e["variants"],
        G[e["gender"]],
        e["tribes"],
        [[m["text"], m["tribes"], m["count"]] for m in e["meanings"]],
        e["pronunciation"],
        [n for n in e["notes"] if n != "Gender inferred from the meaning."],
        e["submissions"],
        int("Tribe marked uncertain" in e["issues"]),
    ]
    for e in d["names"]
    if not e["surname"]
]
surnames = [e["name"] for e in d["names"] if e["surname"]]
data = json.dumps({"n": out, "s": surnames}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

with open(os.path.join(root, "src", "template.html"), encoding="utf-8") as f:
    template = f.read()
assert template.count("__DATA__") == 1, "template.html must contain __DATA__ exactly once"

with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as f:
    f.write(template.replace("__DATA__", data))
print(f"Built index.html with {len(out)} names and {len(surnames)} family names")
