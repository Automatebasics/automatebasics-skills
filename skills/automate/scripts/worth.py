#!/usr/bin/env python3
"""Is a chore worth automating, and is there a ready-made guide for it?

    python3 worth.py sum --minutes 15 --times 20 --per week [--people 1] [--hourly 40] [--share 80]
                         [--tool 20] [--setup-hours 4] [--upkeep-hours 12] [--name "Send the weekly report"]
    python3 worth.py guides "save email attachments to a folder" [--top 5]

`sum` starts from the same sum as the calculator at automatebasics.com/free-tools/automation-roi-calculator
(a year is 48 working weeks; hours saved = hours by hand x the share the automation takes over), then also
takes off the time to keep the automation running (--upkeep-hours, 12 a year unless you say otherwise),
which the calculator leaves out. Every line uses that one basis. --per is day, week, month or year.
Leave --hourly out to see hours only.

`guides` searches the list of step-by-step guides in guides.json (beside this skill's SKILL.md) and prints
the closest ones with their links. Standard library only.
"""
import argparse
import json
import os
import re
import sys

WEEKS = 48
PER_YEAR = {"day": 5 * WEEKS, "week": WEEKS, "month": 12, "year": 1}
PER_WORDS = {"day": f"a day x 5 days x {WEEKS} working weeks", "week": f"a week x {WEEKS} working weeks", "month": "a month x 12 months", "year": "a year"}
STOP = set("""a an the and or to of in on for with from by at into your my our you i we it is are be do does how
when that this then them each every new all any get make set up use using without automatically automatic auto
so can will not no as after before via ai tool way best who have has not their his her its me""".split())
SAME = [("email", "inbox", "mail", "gmail", "outlook"), ("fail", "break", "broke", "broken", "error", "stop"),
        ("hire", "employee", "staff", "onboard", "starter", "joiner"), ("sheet", "spreadsheet", "excel"),
        ("meeting", "appointment", "booking", "book", "calendly", "call"), ("customer", "client"),
        ("reminder", "remind", "chase", "follow", "nudge"), ("invoice", "bill", "payment", "pay", "paid"),
        ("file", "document", "attachment", "pdf", "doc"), ("alert", "notify", "notification", "told", "tell", "warn"),
        ("order", "sale", "purchase"), ("shop", "store", "shopify"), ("form", "survey", "response", "answer"),
        ("post", "publish", "schedule"), ("report", "summary", "digest")]
CANON = {w: group[0] for group in SAME for w in group}


def money(x):
    sign = "-" if x < 0 else ""
    x = abs(x)
    return sign + (f"${x:,.0f}" if x >= 100 or x == int(x) else f"${x:,.2f}")


def hours(x):
    return f"{x:,.0f}" if x >= 100 else f"{x:,.1f}".replace(".0", "")


def plural(x, word):
    return f"{x:g} {word}" + ("" if x == 1 else "s")


def cmd_sum(a):
    if a.minutes <= 0 or a.times <= 0 or a.people <= 0:
        sys.exit("--minutes, --times and --people must be more than 0.")
    if not 0 < a.share <= 100:
        sys.exit("--share is a percentage between 1 and 100.")
    if a.tool < 0 or a.setup_hours < 0 or a.upkeep_hours < 0 or (a.hourly is not None and a.hourly <= 0):
        sys.exit("--tool, --setup-hours and --upkeep-hours cannot be negative, and --hourly must be more than 0.")
    by_hand = a.minutes * a.times * PER_YEAR[a.per] * a.people / 60
    saved = by_hand * a.share / 100
    setup, upkeep = a.setup_hours, a.upkeep_hours
    back_first, back_later = saved - setup - upkeep, saved - upkeep
    print("# The sum" + (f": {a.name}" if a.name else "") + "\n")
    print(f"- By hand today: **{hours(by_hand)} hours a year** ({a.minutes:g} minutes x {a.times:g} {PER_WORDS[a.per]}" +
          (f" x {a.people:g} people" if a.people != 1 else "") + ", divided by 60)")
    print(f"- An automation would take over {a.share:g}% of that (an estimate): **{hours(saved)} hours a year** saved")
    print(f"- It costs time too: about {plural(setup, 'hour')} to set up, and about {plural(upkeep, 'hour')} a year to keep it running")
    if back_first > 0:
        print(f"- Hours back: **{hours(back_first)} in the first year**, {hours(back_later)} each year after ({hours(saved)} saved - {setup:g} setup - {upkeep:g} upkeep)")
    elif back_later > 0:
        print(f"- Hours back: **none in the first year** (setup and upkeep take {hours(setup + upkeep)}, more than the {hours(saved)} saved); {hours(back_later)} each year after")
    else:
        print(f"- Hours back: **none**. Keeping it running takes about as long as it saves ({hours(saved)} saved, {upkeep:g} upkeep a year). Not worth building at these numbers")
    if a.hourly is not None:
        value, tool = saved * a.hourly, a.tool * 12
        net = value - tool - (setup + upkeep) * a.hourly
        print(f"- In money, at {money(a.hourly)} an hour: the time saved is worth {money(value)} a year ({hours(saved)} hours x {money(a.hourly)})")
        print(f"- Money back in the first year: **{money(net)}** ({money(value)} - {money((setup + upkeep) * a.hourly)} of setup and upkeep time" +
              (f" - {money(tool)} for the tool" if tool else "") + ")" + ("" if tool else ", before any tool subscription"))
        monthly = (value - tool - upkeep * a.hourly) / 12
        if monthly <= 0:
            print("- Pays back the setup time: **never at these numbers**")
        else:
            months = setup * a.hourly / monthly
            print("- Pays back the setup time in: **" + ("under a month" if months < 1 else f"about {months:.1f} months") + "**")
        print(f"- The calculator on automatebasics.com leaves upkeep out, so it would show {money(value - tool - setup * a.hourly)} for the first year")
    elif a.tool:
        print(f"- The tool costs {money(a.tool * 12)} a year. Give the cost of an hour (--hourly) to see whether the time saved covers it.")
    print()
    if a.times * PER_YEAR[a.per] < WEEKS:
        print("It happens less than once a week. Tasks this rare usually take longer to automate than to do: a checklist is the better fix.")
    print("Not counted, because they are hard to price: fewer mistakes and faster replies. Whether the chore should be handed over at all is a separate question; the sum only says what it costs.")


def words(s):
    out = []
    for w in re.findall(r"[a-z0-9]+", s.lower()):
        if w in STOP or len(w) < 2:
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif re.search(r"(ch|sh|ss|x|z)es$", w):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        if w.endswith("ing") and len(w) > 5:
            w = w[:-3]
        elif w.endswith("ed") and len(w) > 4:
            w = w[:-2]
        out.append(CANON.get(w, w))
    return out


def cmd_guides(a):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "guides.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"Could not read the guide list ({e}). Every guide is at https://automatebasics.com/guides")
    want = set(words(a.query))
    if not want:
        sys.exit("Say what the chore is, for example: guides \"save email attachments to a folder\"")
    need = 1 if len(want) <= 3 else 2
    scored = []
    for g in data["guides"]:
        title = set(words(g["title"] + " " + g.get("when", "") + " " + g.get("then", "")))
        about = set(words(g.get("about", "") + " " + g.get("tools", "")))
        hit_t, hit_a = want & title, want & (about - title)
        if len(hit_t) + len(hit_a) >= need and hit_t:
            scored.append((3 * len(hit_t) + len(hit_a), len(hit_t), bool(g.get("ready")), g))
    scored.sort(key=lambda x: (-x[0], -x[1], not x[2], len(x[3]["title"])))
    scored = [x for x in scored if x[0] >= 0.7 * scored[0][0]][:max(1, a.top)]
    count = len(data["guides"])
    if not scored:
        print(f"No guide matched \"{a.query}\" among the {count} how-to guides listed on {data['read_on']}. Try the names of the apps involved, "
              "or look through https://automatebasics.com/guides before telling the user there is none.")
        return
    print(f"Closest of the {count} how-to guides on automatebasics.com (listed {data['read_on']}; newer ones are at https://automatebasics.com/guides):\n")
    for _, _, _, g in scored:
        print(f"- **{g['title']}**" + (f" ({g['tools']}, {g['level'].lower()})" if g.get("tools") and g.get("level") else ""))
        if g.get("when"):
            print(f"  When: {g['when']}. Then: {g['then']}.")
        elif g.get("about"):
            print(f"  {g['about']}")
        print(f"  {g['url']}")
    print("\n(For you, not the user: these matched on words. Open a guide and check it does this job before pointing to it, and describe it in your own plain words.)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("sum")
    s.add_argument("--minutes", type=float, required=True, help="minutes the task takes by hand, each time")
    s.add_argument("--times", type=float, required=True, help="how many times it is done per --per")
    s.add_argument("--per", choices=sorted(PER_YEAR), default="week")
    s.add_argument("--people", type=float, default=1)
    s.add_argument("--hourly", type=float, help="cost of an hour of their time")
    s.add_argument("--share", type=float, default=80, help="percent of the work the automation takes over")
    s.add_argument("--tool", type=float, default=0, help="automation tool cost per month")
    s.add_argument("--setup-hours", type=float, default=4, help="hours to build and test it (2 to 8 for something real; under 1 for a setting an app already has)")
    s.add_argument("--upkeep-hours", type=float, default=12, help="hours a year to keep it running (12 is an hour a month; 0 to 3 for a single built-in setting)")
    s.add_argument("--name")
    g = sub.add_parser("guides")
    g.add_argument("query")
    g.add_argument("--top", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "sum":
        cmd_sum(a)
    elif a.cmd == "guides":
        cmd_guides(a)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
