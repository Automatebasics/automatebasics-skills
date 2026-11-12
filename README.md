# Automate Basics skills for Claude

Five free skills for the chores that eat a working week: sorting email, going through a spreadsheet row by row, writing up a meeting, checking what an AI wrote before it goes out, and working out what is worth automating at all. Each one runs inside Claude, on something you paste or upload, with nothing to sign up for. Each one ends by pointing to the free guide on [Automate Basics](https://automatebasics.com) that makes the same job happen on its own.

| Skill | Ask Claude | What you get |
|---|---|---|
| [`inbox`](#inbox) | "Sort my inbox" | Every email under one label with the reason, and draft replies for the ones that need an answer |
| [`rows`](#rows) | "Do this for every row" | Your spreadsheet with a new column filled in, and proof no row was skipped or made up |
| [`notes`](#notes) | "Write up this meeting" | What was decided, who does what by when, what is still open, each with the words it came from |
| [`check`](#check) | "Check this before I send it" | Every number, name, quote and link in an AI-written draft, and anything the AI added, marked confirmed, wrong or not checked |
| [`automate`](#automate) | "Should I automate this?" | A verdict, the hours it gives back, and the steps written out so building it is copying |

The skills only read and draft. They never send an email, delete anything, change your files or connect to an app on their own.

## Why these are skills and not prompts

Each skill carries a small script that does the part an AI is bad at: counting.

- `inbox` will not show a sorted list until every email has exactly one label.
- `rows` will not write the finished file until every row has exactly one answer.
- `notes` looks for each quoted line in the transcript and rejects quotes that are not there, owners who did not take the task and dates nobody said.
- `check` tries the sums behind every worked-out number and opens every link.
- `automate` does the sum the way the [automation ROI calculator](https://automatebasics.com/free-tools/automation-roi-calculator) does, then takes off the time it costs to keep an automation running.

## What Automate Basics is

[Automate Basics](https://automatebasics.com) publishes ready-to-use AI automations for work: free step-by-step guides written as "when this happens, do that", side-by-side comparisons of the tools, and one plain-English email a week on what changed in AI and how to use it at work.

A skill does the job when you ask. A guide sets it up to run without you:

| Skill | When you ask Claude | Set up once, from the guide |
|---|---|---|
| `inbox` | Sorts the mail you give it | [New mail is sorted as it arrives, with the unsure ones held for you](https://automatebasics.com/guides/how-to-automate-email-classification-without-coding) |
| `rows` | Fills the column for the rows in the file | [Each new row in a Google Sheet is read and answered](https://automatebasics.com/guides/connect-claude-to-google-sheets-without-writing-code) |
| `notes` | Writes up the transcript you give it | [Every Google Meet call is transcribed into a Doc](https://automatebasics.com/guides/set-up-google-meet-to-take-notes-automatically) |
| `check` | Checks the draft you give it | [The one-minute version, to do on everything](https://automatebasics.com/articles/sixty-second-verification-pass) |
| `automate` | Plans the automation | [Setups you can copy](https://automatebasics.com/automations) |

## Install a skill

**In Claude Code**, run the line under the skill you want, then start a new session and type its name, for example `/inbox`. To install all five:

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills
```

**In the Claude apps** (web and desktop):

1. Download the skill's zip from the link under it.
2. In Claude open **Customize**, then **Skills**, click **+**, then **Create skill**, then **Upload a skill**, and choose the zip.
3. Skills run code, so **Code execution and file creation** must be on under **Settings**, then **Capabilities**.
4. Ask in plain words, for example "sort these emails" with the file attached.

`check` opens the links in a draft from code. In the Claude apps that needs network access allowed for code execution, in the same Capabilities screen. Without it the skill opens the links with Claude's own web tool, or lists them for you to open.

If you have switched on a connector in Claude for your email or calendar, `inbox` and `automate` can read from it. Nothing needs one.

The scripts need Python 3.8 or later and nothing else.

## inbox

Sorts a pile of email into what needs a reply today, what can wait, what to file and what to ignore, gives the reason for each, and drafts the replies. Works on pasted emails or an exported mailbox (`.mbox`, `.eml`, Outlook `.csv`).

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills/inbox
```

Claude apps: [inbox.zip](https://github.com/automatebasics/automatebasics-skills/raw/main/dist/inbox.zip)

## rows

Does one job on every row of a spreadsheet (sort it into a category, pull out a detail, tidy it, write a line for it) and puts the answers in a new column. Works on `.csv` and `.xlsx`.

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills/rows
```

Claude apps: [rows.zip](https://github.com/automatebasics/automatebasics-skills/raw/main/dist/rows.zip)

## notes

Turns a meeting transcript from Zoom, Google Meet, Teams or a recorder into decisions, tasks with an owner and a date, open questions and what was not agreed, then drafts the follow-up email.

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills/notes
```

Claude apps: [notes.zip](https://github.com/automatebasics/automatebasics-skills/raw/main/dist/notes.zip)

## check

Goes through an AI-written email, summary or report before you send it: the numbers, the names, quotes and links, the sentence a reader will act on, and what is missing.

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills/check
```

Claude apps: [check.zip](https://github.com/automatebasics/automatebasics-skills/raw/main/dist/check.zip)

## automate

Takes a chore you keep doing by hand, says whether it is worth automating, and writes the steps out as a "when this happens, do that" recipe with the simplest tool and a matching guide.

```bash
mkdir -p ~/.claude/skills && curl -sL https://github.com/automatebasics/automatebasics-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 automatebasics-skills-main/skills/automate
```

Claude apps: [automate.zip](https://github.com/automatebasics/automatebasics-skills/raw/main/dist/automate.zip)

## What is in this repository

- `skills/<name>/SKILL.md`: the instructions Claude follows. `scripts/` beside it holds the small Python script the skill runs.
- `skills/automate/guides.json`: the list of Automate Basics how-to guides the `automate` skill searches, with the date it was read.
- `dist/<name>.zip`: the same skill, packed for upload to the Claude apps. `bash build.sh` rebuilds them.
- [`TESTING.md`](TESTING.md): what each skill returned when a fresh Claude ran it, the faults that turned up, and what is still untested.

## Links

- Automate Basics: [automatebasics.com](https://automatebasics.com)
- Ready-to-use automations: [automatebasics.com/automations](https://automatebasics.com/automations)
- Every guide: [automatebasics.com/guides](https://automatebasics.com/guides)
- The weekly email: [automatebasics.com/newsletter](https://automatebasics.com/newsletter)

## License

MIT. The skills are free to use and change.
