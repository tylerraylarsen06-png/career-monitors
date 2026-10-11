# career-monitors

Career pages change without warning. A sophomore program opens, a deadline appears, an Apply button shows up on a page that has said "coming soon" for a month. This repo watches those pages for you and sends a push to your phone when one of them actually changes.

It runs entirely on GitHub Actions. There is no server, no database and no hosting bill. Each monitor is one YAML file, and with Claude Code you can add one by saying "watch JPMorgan's careers page."

Built by Tyler Larsen.

## What it does

Once a day a scheduled workflow:

1. Fetches every page listed in `config/`.
2. Scopes each page down to the part that matters (a CSS selector, regex or JSON path) and normalizes it.
3. Hashes the result and compares it with the last run, stored in `state/` in this repo.
4. If anything changed, optionally asks Gemini whether the change matters to you, using `profile.md` and the monitor's `goal`.
5. Sends one push to your phone through [ntfy](https://ntfy.sh) and, if configured, one Discord message.
6. Commits `state/` back to the repo, so the next run can read it.

The repo is the database. The git history of `state/` is a free audit log of every page.

## How a monitor is defined

One file per monitor in `config/`. The filename becomes its state key.

```yaml
name: "JPMorganChase Programs"
url: "https://www.jpmorganchase.com/careers/explore-opportunities/programs"
type: html                  # html | rss | json
selector: "main"            # optional, html only: scope to this element
regex: 'Applications (are now \w+)'   # optional, any type
json_path: "data.jobs"      # optional, json only
min_content_length: 500     # shorter than this counts as a failed fetch
goal: >
  Alert when a new US undergraduate program appears or an application
  opens. Ignore layout and wording changes.
```

`goal` is plain English. It tells the AI pass what counts for this page in particular, on top of the general rules in `profile.md`.

The included configs watch student and early-career pages at McKinsey, Bain, BCG, Kearney, Oliver Wyman, Roland Berger, Goldman Sachs, Morgan Stanley, JPMorganChase, Citi and Bank of America, plus a public GitHub list of underclassmen internships.

## Adding a firm

**With Claude Code.** Open the repo and say what you want:

```
watch JPMorgan's careers page
```

Claude finds the careers URL, checks which element holds the listings, writes `config/jpmorgan-careers.yaml` with a `goal` based on your profile, and commits it. `CLAUDE.md` in this repo tells it how.

**By hand.** Copy any file in `config/`, change `name`, `url` and `goal`, and pick a `selector` that wraps the listings (open the page, inspect the element, use its tag, id or class). Leave `selector` out to watch the whole page, which works but picks up more noise.

The first run after you add a monitor records a baseline and sends nothing. Changes are reported from the second run on.

## Setup

1. Fork or copy this repo to your GitHub account.
2. Copy `profile.example.md` to `profile.md` and fill in who the alerts are for. Without it, the example profile is used.
3. Install the ntfy app on your phone ([iOS](https://apps.apple.com/app/ntfy/id1625396347), [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)). Tap **+** and subscribe to a topic name that is long and hard to guess, such as `career-alerts-7f3k9q2m`. ntfy needs no account, so the topic name is the only thing protecting it.
4. Add repository secrets under **Settings > Secrets and variables > Actions**, or with `gh secret set NAME`:

   | Secret | Required | Purpose |
   |---|---|---|
   | `NTFY_TOPIC` | For phone alerts | The topic from step 3. One push per run that saw a change. Skipped if unset. |
   | `GEMINI_API_KEY` | No | Turns on the AI judgment pass. Free key from [Google AI Studio](https://aistudio.google.com/apikey). |
   | `DISCORD_WEBHOOK_URL` | No | Also posts a full digest, including failures, to a Discord channel. |
   | `DISCORD_USER_ID` | No | @-mentions you in Discord when a change is worth acting on. |

5. Run it once by hand: **Actions > monitor > Run workflow**, or `gh workflow run monitor.yml`. After that it runs daily at 06:00 UTC (edit the cron in `.github/workflows/monitor.yml` to change it).

If the "Commit and push state" step fails with a permissions error, set **Settings > Actions > General > Workflow permissions** to read and write.

## How notifications work

When a run sees a change, it sends one ntfy push that summarizes every changed monitor. With a Gemini key the push carries Gemini's one-line verdict per page, such as what opened and what to do. Without one it lists each changed page and its URL. When exactly one page changed, tapping the notification opens it.

Priority follows the AI verdict:

| Situation | Push priority | Discord ping |
|---|---|---|
| Gemini judged a change meaningful | High | Yes |
| Gemini judged every change as noise | Low | No |
| Gemini unavailable, something changed | High | Yes |
| No changes, only failing fetches | No push | No |

An unknown is never treated as safe to ignore. If the AI call fails, you still hear about the change.

## Not crying wolf

Most of the work is in not reporting things that did not happen.

- **Scope before hashing.** A rotating banner or a new blog post elsewhere on the page does not count as a change.
- **Soft-404 protection.** A request error, a selector that matches nothing, or text shorter than `min_content_length` marks the monitor as failed, never changed. A bot-check page is short, so it never overwrites good state.
- **Failures wait.** A monitor only appears under failures in the Discord digest after three consecutive failed runs.
- **The AI is a filter, not the detector.** Change detection is a plain hash comparison. Gemini only decides how loudly to tell you.
- **Keeping the cron alive.** GitHub disables scheduled workflows after 60 days without repo activity. Every run rewrites `state/_heartbeat.json`, so every run commits and the timer never runs out.

A known limit: pages that render their listings with JavaScript, or sit behind bot protection, can come back empty to a plain HTTP fetch. Those monitors show up as failures instead of false changes. Fixing them needs a headless browser, which this design leaves out on purpose.

## Files

| Path | What it does |
|---|---|
| `config/*.yaml` | One monitor per file |
| `monitors/` | Fetchers for `html`, `rss` and `json`, plus shared normalizing, hashing and diffing in `common.py` |
| `run.py` | Checks every monitor, diffs against state, sends the push and the digest |
| `translate.py` | Optional Gemini pass that judges each word-level diff |
| `digest.py` | Builds the Discord digest and the ntfy push |
| `profile.example.md` | Template for `profile.md`, the plain-text description of who the alerts are for |
| `tests/` | Offline tests for the push and the run wiring |
| `.github/workflows/monitor.yml` | The schedule, the run and the state commit |

## Running locally

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m unittest discover tests   # offline, no network
NTFY_TOPIC=your-topic python3 run.py  # real run, fetches every page
```

Every secret is optional locally. With none set, a run still fetches, diffs and writes `state/`, and just skips sending.

## Roadmap

- **Monitor creation as a one-line command.** A Claude Code command such as `/watch JPMorgan` that finds the page, tests a selector against a live fetch, writes the config and opens a pull request.
- **Alerts into Apple Reminders.** Turn a meaningful change into a reminder with the deadline as its due date, so "applications open" becomes a task instead of a notification you swipe away.

Built with Chewbacca
