#!/usr/bin/env bash
# Checks the skills and builds dist/<skill>.zip for upload to the Claude apps.
#   bash build.sh          check, then rebuild the zips
#   bash build.sh --check  check only
# Fails if a skill's SKILL.md breaks the upload rules, or if the guide list in skills/automate is not valid.
set -euo pipefail
cd "$(dirname "$0")"
[ "${1:-}" = "--check" ] && CHECK=1

CHECK="${CHECK:-}" python3 - <<'PY'
import json, os, re, sys, zipfile
ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}  # what the Claude apps accept
bad = 0
try:
    guides = json.load(open("skills/automate/guides.json", encoding="utf-8"))["guides"]
    assert guides and all(g.get("title") and g.get("url", "").startswith("https://automatebasics.com/") for g in guides)
except Exception as e:
    bad += 1
    print(f"skills/automate/guides.json: {e!r}")
for name in sorted(os.listdir("skills")):
    path = os.path.join("skills", name, "SKILL.md")
    if not os.path.isfile(path):
        continue
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    keys = dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M)) if m else {}
    desc = keys.get("description", "").strip('"')
    problems = []
    if keys.get("name") != name: problems.append("name must equal the folder name")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name): problems.append("name: lower-case letters, digits and hyphens only")
    if not 1 <= len(desc) <= 1024: problems.append(f"description is {len(desc)} characters (limit 1024)")
    if set(keys) - ALLOWED: problems.append(f"keys the Claude apps reject: {sorted(set(keys) - ALLOWED)}")
    if len(text.splitlines()) > 500: problems.append("SKILL.md is over 500 lines")
    for script in re.findall(r"python3 (scripts/[\w.-]+)", text):
        if not os.path.isfile(os.path.join("skills", name, script)): problems.append(f"SKILL.md runs {script}, which is not in the skill")
    for p in problems:
        bad += 1
        print(f"{name}: {p}")
    if problems or os.environ.get("CHECK"):
        continue
    os.makedirs("dist", exist_ok=True)
    with zipfile.ZipFile(f"dist/{name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(os.path.join("skills", name)):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in sorted(files):
                if f.endswith(".pyc") or f == ".DS_Store":
                    continue
                full = os.path.join(root, f)
                info = zipfile.ZipInfo(os.path.relpath(full, "skills"), date_time=(2026, 1, 1, 0, 0, 0))  # fixed date: same input, same zip
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, open(full, "rb").read())
    print(f"built dist/{name}.zip")
sys.exit(1 if bad else 0)
PY
