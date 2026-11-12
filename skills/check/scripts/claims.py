#!/usr/bin/env python3
"""List everything in a draft that could be wrong: every number, name, quote and link, and the sentences a
reader may act on. With the material the draft was written from, say which of them are in it.

    python3 claims.py draft.txt [--source notes.txt more.csv ...] [--links] [--json claims.json]

    --source  the notes, figures or documents the draft was written from (.txt .md .csv .docx .html).
              Each number, name and quote is then marked "in your material" or "NOT in your material".
    --links   open each link (one a second) and report whether it works, where it lands, the page's title,
              and whether the numbers and names in the same sentence are on that page.

It finds things to check; it does not decide what is true. A number that is "in your material" was copied
correctly, which is not the same as being right. Reads .txt, .md, .docx and .html. Standard library only.
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

UA = "Mozilla/5.0 (compatible; AutomateBasicsSkills/1.0; +https://github.com/automatebasics/automatebasics-skills)"
MONTHS = "january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec".split()
DAYS = "monday tuesday wednesday thursday friday saturday sunday".split()
PLAIN = set(MONTHS + DAYS + """i the a an this that these those it we you they he she our your their my his her its if in on at
to for from with and or but so as by of not no yes hi hello dear thanks thank regards best please note also however
when what why how who where which while after before since until once there here each every all some most many
few both either neither one two three four five six seven eight nine ten first second third next last new now then
today tomorrow yesterday summary overview background key update subject re fwd ok q1 q2 q3 q4 am pm ai""".split())
MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}
NUM = re.compile(r"(?<![\w.,/-])([$£€]\s?)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s?(?:%|percent\b|per cent\b|k\b|m\b|bn\b|million\b|billion\b|thousand\b))?(?![\w/]|[.,-]\d)", re.I)
URL = re.compile(r"https?://[^\s<>\"')\]]+")
OTHER = [("time", re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm|a\.m\.|p\.m\.)(?!\w)|\b\d{1,2}:\d{2}\b", re.I)),
         ("date", re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.](?:\d{4}|\d{2})\b|\b\d{1,2}/\d{1,2}\b")),
         ("range", re.compile(r"\b\d+(?:[.,]\d+)?\s?[-–]\s?\d+(?:[.,]\d+)?\s?%?(?=\s|$|[,.;:)])")),
         ("times", re.compile(r"\b\d+(?:\.\d+)?x\b", re.I)),
         ("decade", re.compile(r"\b\d{4}s\b|\b'\d0s\b"))]
UP = re.compile(r"\b(up|rise|rose|risen|increase[sd]?|grew|grown|growth|more|higher|gain(?:ed)?|jump(?:ed)?)\b", re.I)
DOWN = re.compile(r"\b(down|fall|fell|fallen|drop(?:ped)?|decrease[sd]?|cut|less|lower|sav(?:e|ed|ing|ings)|off|discount(?:ed)?|reduc(?:e|ed|tion))\b", re.I)
ACT2 = re.compile(r"\bby \d|[$£€]\s?\d|\byou(?:'ll| will)? pay\b|\btotal\b|\bvalid until\b|\bexpires?\b|\bwithin \d", re.I)
WEEKDAY_DATE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]{3})[a-z]*\.?(?:,?\s+(\d{4}))?"
                          r"|\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?", re.I)
ACT = re.compile(r"\b(will|won't|must|shall|deadline|due|by (?:the )?(?:end|close|eod|" + "|".join(MONTHS + DAYS) + r"|\d)|no later than|guarantee[sd]?|"
                 r"confirm(?:ed|s)?|agreed|approved|allows?|permits?|permitted|entitled|required|always|never|refund|penalt\w+|notice period|"
                 r"free of charge|at no (?:extra |additional )?cost|included?s?|we can|you can|is able to|has capacity|commit\w*|promise[sd]?|"
                 r"costs?|priced?|a month|per month|a year|per year|automatically|retried|every time)\b", re.I)


def read_any(path):
    low = path.lower()
    try:
        if low.endswith(".docx"):
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            paras = re.findall(r"<w:p[ >].*?</w:p>", re.sub(r"<w:(tab|br)[^>]*/>", " ", xml), re.S)
            return "\n".join(html.unescape(re.sub(r"<[^>]+>", "", p)) for p in paras)
        text = open(path, encoding="utf-8-sig", errors="replace").read()
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        sys.exit(f"Could not read {path}: {e}")
    if low.endswith((".pdf", ".xlsx", ".pptx", ".doc")):
        sys.exit(f"{path}: this kind of file cannot be read here. Copy its text into a .txt file and give that.")
    if low.endswith((".html", ".htm")):
        text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)))
    return text


def sentences(text):
    out = []
    for block in re.split(r"\n+", text):
        block = re.sub(r"^\s*(?:[-*•>]+|#+|\d{1,2}[.)])\s+", "", block).strip()   # bullets, headings, list numbers
        if not block:
            continue
        links = []
        safe = URL.sub(lambda m: links.append(m.group(0)) or f"\x00{len(links) - 1}\x00", block)  # dots in links are not sentence ends
        for s in re.split(r"(?<=[.!?])[\"”’)]?\s+(?=[\"“‘(\[]?[A-Z0-9$£€\x00])", safe):
            s = re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], s).strip()
            if s:
                out.append(s)
    return out


def value(m):
    n = float(m.group(2).replace(",", "") + (m.group(3) or ""))
    unit = (m.group(4) or "").strip().lower()
    return n * MULT.get(unit, 1)


def kind(m):
    unit = (m.group(4) or "").strip().lower()
    if m.group(1):
        return "money"
    before = re.findall(r"[A-Za-z]+", m.string[max(0, m.start() - 12):m.start()])
    after = re.match(r"(?:st|nd|rd|th)?\s+([A-Za-z]+)", m.string[m.end():])
    if not unit and not m.group(3) and ((after and after.group(1).lower() in MONTHS) or (before and before[-1].lower() in MONTHS)):
        return "date"
    if unit in ("%", "percent", "per cent"):
        return "percent"
    if not m.group(3) and not unit and "," not in m.group(2) and 1900 <= int(m.group(2)) <= 2100:
        return "year"
    return "number"


def others_in(text):
    """Times, slash dates, ranges, "2x" and decades: number-like things the main pattern does not list."""
    text, out = URL.sub(" ", text), []
    for knd, rx in OTHER:
        for m in rx.finditer(text):
            if not any(m.start() < e and s0 < m.end() for s0, e, _, _ in out):
                out.append((m.start(), m.end(), m.group(0).strip(), knd))
    return sorted(out)


def blank_others(text):
    text = URL.sub(" ", text)
    for s0, e, _, _ in others_in(text):
        text = text[:s0] + " " * (e - s0) + text[e:]
    return text


def numbers_in(text):
    return [(m.group(0).strip(), value(m), kind(m), m) for m in NUM.finditer(blank_others(text))]


def squash(t):
    return re.sub(r"[\s.]", "", t.lower().replace("–", "-"))


def close(a, b, places):
    return abs(a - b) <= 0.5 * 10 ** (-places) + 1e-9


def worked_out(token, val, knd, beside, before, sentence=""):
    """Can this number be made from the numbers beside it? Returns a short note for the "sum" column, or ''."""
    places = len(re.sub(r"\D", "", token.split(".")[1])) if "." in token else 0
    fmt = lambda x: f"{x:,.2f}".rstrip("0").rstrip(".")
    for others in (beside, beside + before):       # the same sentence first, then the one before it
        vals = sorted({v for v in others if v != val})[:12]
        for i, lo in enumerate(vals):
            for hi in vals[i + 1:]:
                tries = []
                if knd == "percent" and lo:
                    up, down = bool(UP.search(sentence)), bool(DOWN.search(sentence))
                    if not down or up:
                        tries.append(((hi - lo) / lo * 100, f"the rise from {fmt(lo)} to {fmt(hi)}"))
                    if not up or down:
                        tries.append(((hi - lo) / hi * 100, f"the fall from {fmt(hi)} to {fmt(lo)}"))
                    tries += [(lo / hi * 100, f"{fmt(lo)} as a share of {fmt(hi)}"), (hi / lo * 100, f"{fmt(hi)} as a share of {fmt(lo)}")]
                elif knd != "percent":
                    tries += [(hi - lo, f"{fmt(hi)} minus {fmt(lo)}"), (hi + lo, f"{fmt(hi)} plus {fmt(lo)}"), (hi * lo, f"{fmt(hi)} times {fmt(lo)}")]
                    if lo:
                        tries.append((hi / lo, f"{fmt(hi)} divided by {fmt(lo)}"))
                for got, how in tries:
                    if close(got, val, places):
                        return f"equals {how}: confirm that is the right sum"
        if knd != "percent":                         # a week, month or hour turned into a year or a day
            for x in vals:
                for got, how in ((x * 12, f"{fmt(x)} x 12 months"), (x * 52, f"{fmt(x)} x 52 weeks"), (x * 48, f"{fmt(x)} x 48 working weeks"),
                                 (x * 52 / 60, f"{fmt(x)} minutes x 52 weeks, in hours"), (x * 48 / 60, f"{fmt(x)} minutes x 48 working weeks, in hours"),
                                 (x * 5, f"{fmt(x)} x 5 days"), (x * 365, f"{fmt(x)} x 365 days"), (x / 60, f"{fmt(x)} minutes in hours")):
                    if close(got, val, places):
                        return f"equals {how}: confirm that is the right sum"
    vals = sorted({v for v in beside if v != val})
    if knd == "percent" and len(vals) >= 2:
        lo, hi = vals[0], vals[-1]
        if UP.search(sentence) and not DOWN.search(sentence) and lo:
            return f"**does not work out**: from {fmt(lo)} to {fmt(hi)} is a rise of {(hi - lo) / lo * 100:.1f}%"
        if DOWN.search(sentence) and not UP.search(sentence) and hi:
            return f"**does not work out**: from {fmt(hi)} to {fmt(lo)} is a fall of {(hi - lo) / hi * 100:.1f}%"
        return (f"**does not work out** from the numbers beside it ({fmt(lo)} is {lo / hi * 100:.1f}% of {fmt(hi)}; "
                f"from {fmt(lo)} to {fmt(hi)} is a rise of {(hi - lo) / lo * 100:.1f}%)" if lo and hi else "**does not work out** from the numbers beside it")
    if vals:
        return "may have been worked out from the numbers beside it: do the sum"
    return ""


def names_in(sents):
    found = {}
    for si, s in enumerate(sents):
        s2 = URL.sub(" ", s)
        for m in re.finditer(r"\b(?:[A-Z][\w'’.-]*|[a-z]+[A-Z]\w*)(?:\s+(?:of|the|&|de|van|von|for)\s+(?=[A-Z])|\s+(?=[A-Z])|(?=\b))(?:(?:[A-Z][\w'’.-]*)(?:\s+(?:of|the|&|de|van|von|for)\s+(?=[A-Z])|\s+(?=[A-Z]))?)*", s2):
            name = re.sub(r"['’]s\b", "", m.group(0).strip()).rstrip(".,'’")
            words = name.split()
            while words and words[0].lower() in PLAIN:
                words = words[1:]
            while words and words[-1].lower() in PLAIN | {"of", "the", "and", "&", "for"}:
                words = words[:-1]
            if not words:
                continue
            name = " ".join(words)
            pos = s2.find(words[0], m.start())
            at_start = pos <= len(s2) - len(s2.lstrip("\"“‘([ ")) or s2[:pos].rstrip().endswith(":")
            single = len(words) == 1
            if single and (len(name) < 3 or name.lower() in PLAIN):
                continue
            if single and at_start and not re.search(r"[A-Z].*[A-Z]|\d", name):
                after = s2[pos + len(words[0]):pos + len(words[0]) + 14].lower()
                if not re.match(r"('s|’s)? ?(was|is|has|have|had|will|said|says|confirmed|announced|reports?|found|offers|makes|charges|launched|connects|agreed)\b", after):
                    continue  # an ordinary word that only has a capital because it starts the sentence
            found.setdefault(name, []).append(si)
    return found


def fetch(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read(600000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        try:
            out = subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", UA, "-w", "\n%{http_code} %{url_effective}", url],
                                 capture_output=True, timeout=timeout + 5).stdout.decode("utf-8", "replace")
            body, _, tail = out.rpartition("\n")
            code, _, final = tail.partition(" ")
            if code.isdigit() and int(code):
                return int(code), final or url, body[:600000]
        except Exception:
            pass
        return 0, url, str(e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft")
    ap.add_argument("--source", nargs="*", default=[])
    ap.add_argument("--links", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    draft = read_any(a.draft)
    sents = sentences(draft)
    if not sents:
        sys.exit("The draft is empty.")
    src = "\n".join(read_any(p) for p in a.source)
    have = bool(src.strip())
    src_nums = [(v, k, m) for _, v, k, m in numbers_in(src)]
    src_squash = squash(src)

    def in_notes(val, knd):
        """The same figure, as the same kind of figure (a percent only matches a percent), and where it is."""
        same = {"money": {"money"}, "percent": {"percent"}, "year": {"year"}, "date": {"date"}, "number": {"number"}}[knd]
        for v, k, m in src_nums:
            if k in same and close(val, v, 6):
                st = m.string
                return "\u201c" + re.sub(r"\s+", " ", st[max(0, m.start() - 30):m.end() + 30]).strip() + "\u201d"
        return ""
    src_low = re.sub(r"\s+", " ", src.lower().replace("’", "'"))
    cell = lambda s: s.replace("|", "/").replace("\n", " ")
    short = lambda s, n=150: cell(s if len(s) <= n else s[:n - 1] + "…")
    mark = lambda ok: ("in your notes" if ok else "**NOT in your notes**") if have else "check where it came from"

    print("# What to check in this draft\n")
    print(f"Scope: {len(sents)} sentence(s), {len(draft.split())} words. " +
          (f"Compared with {len(a.source)} file(s) of the user's notes ({len(src.split())} words)." if have else
           "No notes given to compare with, so nothing is marked as the user's: every item below needs a source."))

    # 1. numbers
    rows, out_nums = [], []
    for si, s in enumerate(sents):
        here = numbers_in(s)
        beside = [v for _, v, k, _ in here if k not in ("date", "year")]
        before = [v for _, v, k, _ in numbers_in(sents[si - 1]) if k not in ("date", "year")] if si else []
        for tok, val, knd, _ in here:
            where = in_notes(val, knd)
            ok = bool(where)
            why = "" if knd in ("year", "date") else worked_out(tok, val, knd, beside, before, s)
            if ok and why.startswith("**"):
                why += " (the notes have the same figure, but check it is used for the same thing)"
            elif ok:
                why = ""
            rows.append((tok, knd, ok, why, s, where))
            out_nums.append({"number": tok, "kind": knd, "in_material": ok if have else None, "notes_context": where, "note": why, "sentence": s})
        for _, _, tok, knd in others_in(s):
            ok = squash(tok) in src_squash
            rows.append((tok, knd, ok, "", s, ""))
            out_nums.append({"number": tok, "kind": knd, "in_material": ok if have else None, "note": "", "sentence": s})
    print(f"\n## 1. Numbers ({len(rows)})\n")
    if rows:
        print("| Number | Kind | In your notes? | Does the sum work? | Sentence |")
        print("|---|---|---|---|---|")
        for tok, knd, ok, why, s, where in rows:
            print(f"| {cell(tok)} | {knd} | {mark(ok)}{(' ' + cell(where)) if where else ''} | {why or '-'} | {short(s)} |")
        if have:
            n_not = sum(1 for r in rows if not r[2])
            print(f"\n{n_not} of {len(rows)} number(s) are not in your notes. Each one is checked at its source, worked out again, or cut.")
            print("\"In your notes\" means the same figure appears somewhere in them. It does not mean the notes use it for the same thing: read the two side by side.")
        print("A \"-\" in the sum column means no sum was tried. It is not a pass.")
        print("Numbers written as words (\"three\", \"a dozen\", \"half\") are not listed: read for them.")
    else:
        print("No digits in the draft. Read for numbers written as words.")
    year = re.findall(r"\b(20\d\d)\b", draft)
    year = int(max(set(year), key=year.count)) if year else datetime.date.today().year
    clashes = []
    for m in WEEKDAY_DATE.finditer(draft):
        g = m.groups()
        wd, day, mon, yr = (g[0], g[1], g[2], g[3]) if g[0] else (g[4], g[6], g[5], g[7])
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        if mon.lower()[:3] not in months:
            continue
        try:
            d = datetime.date(int(yr) if yr else year, months.index(mon.lower()[:3]) + 1, int(day))
        except ValueError:
            clashes.append(f"\"{m.group(0)}\" is not a real date")
            continue
        if d.strftime("%a").lower()[:3] != wd.lower()[:3]:
            clashes.append(f"\"{m.group(0)}\": {d:%d %B %Y} is a {d:%A}" + ("" if yr else f" (taking the year as {year})"))
    if clashes:
        print("\n**Weekday and date do not match:**\n- " + "\n- ".join(clashes))

    # 2. names, quotes, links
    names = names_in(sents)
    print(f"\n## 2. Names ({len(names)})\n")
    out_names = []
    if names:
        print("| Name | Times | In your notes? | First used in |")
        print("|---|---|---|---|")
        for name, at in sorted(names.items(), key=lambda kv: (kv[1][0], kv[0])):
            ok = name.lower().replace("’", "'") in src_low
            times = len(re.findall(r"(?<!\w)" + re.escape(name) + r"(?!\w)", draft))
            out_names.append({"name": name, "times": times, "in_material": ok if have else None})
            print(f"| {cell(name)} | {times} | {mark(ok)} | {short(sents[at[0]], 110)} |")
        print("\nThis list is rough: it is every capitalised name the script could see. People, companies, products, laws and places all need to be real and spelled right.")
    quotes = [q for q in re.findall(r"[\"“]([^\"“”]{6,400})[\"”]", draft) + re.findall(r"(?<![\w])[‘']([^‘’'\n]{6,400})[’'](?![\w])", draft) if len(q.split()) >= 2]
    out_quotes = []
    if quotes:
        print(f"\n## Quoted words ({len(quotes)})\n")
        for q in quotes:
            ok = re.sub(r"\s+", " ", q.lower().replace("’", "'")).strip(" .,") in src_low
            out_quotes.append({"quote": q, "word_for_word": ok if have else None})
            print(f"- \"{short(q, 200)}\": " + (("word for word in your notes" if ok else "**NOT found word for word in your notes**") if have else "check it is exact, and who said it"))
    urls = []
    for si, s in enumerate(sents):
        for u in URL.findall(s):
            u = u.rstrip(".,;:!?")
            if u not in [x[0] for x in urls]:
                urls.append((u, si))
    out_links = []
    print(f"\n## Links ({len(urls)})\n")
    if not urls:
        print("None in the draft.")
    elif not a.links:
        for u, si in urls:
            print(f"- {u}")
        print("\nNot opened. Run again with --links, or open each one: a link that works can still say something else.")
    else:
        for i, (u, si) in enumerate(urls[:30]):
            if i:
                time.sleep(1)
            code, final, body = fetch(u)
            title = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
            title = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()[:120] if title else ""
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body))).lower() if 200 <= code < 300 else ""
            page_vals = {v for _, v, _, _ in numbers_in(text)} if text else set()
            s = sents[si]
            in_sent = [(tok, val) for tok, val, knd, _ in numbers_in(s) if knd != "date"]
            miss_n = [tok for tok, val in in_sent if not any(close(val, pv, 6) for pv in page_vals)]
            sent_names = [n for n, at in names.items() if si in at]
            miss_names = [n for n in sent_names if n.lower() not in text]
            path = lambda x: x.split("//")[-1].split("?")[0].rstrip("/").split("/")[1:]
            general = bool(code and path(u) and final.rstrip("/") != u.rstrip("/") and path(u)[-1].lower() not in final.lower())
            state = "works" if 200 <= code < 300 else ("could not be opened" if code == 0 else "page not found" if code in (404, 410) else
                     "the site would not let a script read it: open it yourself" if code in (401, 403, 429) else f"the site answered with error {code}")
            moved = final.split("//")[-1].split("/")[0].replace("www.", "") != u.split("//")[-1].split("/")[0].replace("www.", "")
            out_links.append({"url": u, "status": code, "lands_on": final, "title": title, "numbers_not_on_page": miss_n if text else None, "names_not_on_page": miss_names if text else None})
            if general and 200 <= code < 300:
                state = "sent to a different page"
            out_links[-1]["sent_elsewhere"] = bool(general)
            print(f"- {u}: **{state}**" + (f", lands on {final}" if (moved or general) and code else "") + (f". Page title: \"{title}\"" if title else ""))
            if general and 200 <= code < 300:
                print("  It was sent on to a different page, so the page the draft points to may not exist. Treat what the draft says about it as not checked.")
                continue
            if text and (miss_n or miss_names):
                print(f"  The sentence beside it has " + "; ".join(x for x in (
                    f"number(s) not on that page: {', '.join(miss_n)}" if miss_n else "", f"name(s) not on that page: {', '.join(miss_names)}" if miss_names else "") if x) +
                    ". Read the page before trusting the link.")
            elif text and not in_sent and not sent_names:
                print("  Its sentence has no number or name to compare with the page. Read the page to see whether it says what the draft says.")
            if text and si + 1 < len(sents) and not URL.search(sents[si + 1]):   # the next sentence often leans on the same link
                nxt = sents[si + 1]
                miss2 = [tok for tok, val, knd, _ in numbers_in(nxt) if knd != "date" and not any(close(val, pv, 6) for pv in page_vals)]
                miss2 += [n for n, at in names.items() if si + 1 in at and n.lower() not in text]
                if miss2:
                    print(f"  The sentence after it has things that are not on that page: {', '.join(miss2)}.")
                else:
                    print(f"  The sentence after it may lean on this page too: \"{short(nxt, 90)}\" Read it against the page.")
            if text and (miss_n or miss_names):
                pass
            elif text:
                print("  The numbers and names in its sentence are on the page. Still read the passage: being on the page is not the same as the page saying it.")
        if len(urls) > 30:
            print(f"\n{len(urls) - 30} more link(s) were not opened.")

    # 3. sentences a reader acts on
    acts = [s for s in sents if ACT.search(URL.sub(" ", s)) or ACT2.search(URL.sub(" ", s))]
    print(f"\n## 3. Sentences a reader may act on ({len(acts)})\n")
    for s in acts[:15]:
        print(f"- {short(s, 260)}")
    if len(acts) > 15:
        print(f"- and {len(acts) - 15} more")
    if not acts:
        print("None found by wording. Read the middle of the draft for the sentence that changes what the reader does next.")
    print("\nPick the one a reader is most likely to forward, quote or act on, and check that one hardest.")
    print("\n## 4. What is missing\n\nNo script can list this. Ask: what would a careful reader expect to find here that is not here?")
    if a.json:
        json.dump({"numbers": out_nums, "names": out_names, "quotes": out_quotes, "links": out_links, "act_on": acts},
                  open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
