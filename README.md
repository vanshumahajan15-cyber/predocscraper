# Predoc Scraper

Automated scraper that collects predoctoral research opportunities from [predoc.org](https://www.predoc.org/opportunities) and the [NBER career resources page](https://www.nber.org/career-resources/research-assistant-positions-not-nber), deduplicates listings, saves results to CSV/JSON, and sends daily push notifications via [ntfy.sh](https://ntfy.sh).

Designed for **Render Cron Jobs** (daily 9:00 AM America/Chicago) but runs locally with `python main.py`.

---

## Scraping Strategy

### predoc.org/opportunities

| Element | Purpose |
|---------|---------|
| `<article>` | One job posting per element |
| `article h2 a` | Job title and application URL |
| `div.swiss-text strong` | Labeled metadata fields |

**Fields extracted:** Sponsoring Researcher(s), Sponsoring Institution, Fields of Research, Deadline, Location, Start Date, Visa, and optional Duration/Employment/Salary when present.

**Fallback:** Regex patterns on plain text when `<strong>` tags are malformed (common on predoc.org).

### NBER career resources page

| Element | Purpose |
|---------|---------|
| `div.page-header__intro-inner > p` | One job per paragraph |
| First line before `<br>` | Job title |
| Labeled lines | Researcher, Institution, Research fields, Deadline, Location |
| `<a href>` | Application URL |

**Graceful degradation:** If a site's HTML layout changes, the scraper logs an error for that source and continues with the other source.

---

## Project Structure

```
predocscraper/
├── main.py                 # Entry point
├── config.py               # Settings and paths
├── models.py               # JobRecord dataclass
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   ├── predoc_jobs.csv     # Updated each run
│   └── predoc_jobs.json    # Updated each run
├── logs/
│   └── scraper.log         # Rotating log file
├── scrapers/
│   ├── predoc_scraper.py
│   └── nber_scraper.py
├── services/
│   ├── notifier.py         # ntfy push notifications
│   └── storage.py          # CSV/JSON persistence + dedup
└── utils/
    ├── http.py             # Retries, timeouts, SSL fallback
    ├── logging_setup.py
    ├── normalize.py
    └── dedup.py
```

---

## Installation (Local)

**Requirements:** Python 3.11+

```powershell
cd "c:\Users\vansh\OneDrive\predoc"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional: copy environment template

```powershell
copy .env.example .env
```

---

## Local Execution

```powershell
python main.py
```

**What happens:**
1. Scrapes predoc.org and NBER
2. Deduplicates against existing `data/predoc_jobs.json`
3. Updates `data/predoc_jobs.csv` and `data/predoc_jobs.json`
4. Sends ntfy notification to topic `predoc`
5. Writes logs to `logs/scraper.log`

---

## Deduplication

The same posting is never stored twice. Matching uses three layers:

1. **URL** — normalized application URL
2. **Title + Institution** — case-insensitive match on both fields
3. **Title** — when institution also matches on an existing record

Each record gets a stable `dedup_key` (`url:...` or `hash:...`).

---

## ntfy Setup

1. Install the [ntfy app](https://ntfy.sh/app) on your phone (optional).
2. Subscribe to topic: **`predoc`**
3. Notifications are sent to: `https://ntfy.sh/predoc`

**When new jobs are found:**
- Title: `Predoc Scraper: N new job(s)`
- Body: job titles and institutions

**When no new jobs:**
- Message: `Predoc Scraper: No new opportunities found today.`

Override via environment variables:

| Variable | Default |
|----------|---------|
| `NTFY_TOPIC` | `predoc` |
| `NTFY_BASE_URL` | `https://ntfy.sh` |
| `NTFY_TITLE` | `Predoc Scraper` |

---

## GitHub Actions (Automatic Daily Run — Recommended)

The repo includes a workflow that runs **every day at 9:00 AM America/Chicago**, even when your PC is off.

**File:** `.github/workflows/daily-scrape.yml`

| Setting | Value |
|---------|-------|
| **Schedule** | `0 14,15 * * *` (UTC) with Chicago time check |
| **Timezone** | America/Chicago (9:00 AM) |
| **Command** | `python main.py` |
| **Data persistence** | Commits updated `data/predoc_jobs.csv` and `data/predoc_jobs.json` back to the repo |

### Enable it (one-time)

1. Open [your repo on GitHub](https://github.com/vanshumahajan15-cyber/predocscraper)
2. Go to **Settings → Actions → General**
3. Under **Workflow permissions**, select **Read and write permissions**
4. Save

### Verify

1. Go to the **Actions** tab
2. Click **Daily Predoc Scraper → Run workflow** to test manually
3. Check your ntfy topic `predoc` for a notification

### Manual run anytime

GitHub → **Actions** → **Daily Predoc Scraper** → **Run workflow**

---

## Render Cron Job Deployment

### 1. Push this repo to GitHub

Repository: [vanshumahajan15-cyber/predocscraper](https://github.com/vanshumahajan15-cyber/predocscraper)

### 2. Create a Cron Job on Render

1. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Cron Job**
2. Connect your GitHub repo `predocscraper`
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `predoc-scraper` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Command** | `python main.py` |
| **Schedule** | `0 9 * * *` |
| **Timezone** | `America/Chicago` |

4. Add environment variables (optional):

| Key | Value |
|-----|-------|
| `NTFY_TOPIC` | `predoc` |
| `NTFY_BASE_URL` | `https://ntfy.sh` |

5. **Persistent storage (recommended):** Attach a Render disk mounted at `/opt/render/project/src/data` so job history survives cron runs. Without a disk, each run starts with empty data on Render's ephemeral filesystem.

### 3. Verify

After the first cron run, check Render logs and your ntfy subscription.

---

## GitHub Workflow

### First-time setup

```powershell
cd "c:\Users\vansh\OneDrive\predoc"
git remote add origin https://github.com/vanshumahajan15-cyber/predocscraper.git
git branch -M main
```

### Daily development workflow

```powershell
git status
git add .
git commit -m "Describe your change"
git push
```

### Authentication (Windows)

Use **Git Credential Manager** — when you push, sign in via browser. If prompted for a password, use a GitHub **Personal Access Token** (not your account password).

Create a token: GitHub → Settings → Developer settings → Personal access tokens → **repo** scope.

---

## Output Fields

Each job record includes:

| Field | Description |
|-------|-------------|
| `title` | Job title |
| `institution` | Sponsoring institution |
| `university` | Same as institution (alias) |
| `research_fields` | Field(s) of research |
| `location` | Location if listed |
| `researcher_names` | PI / sponsoring researcher(s) |
| `application_deadline` | Deadline |
| `date_posted` | Start/post date if listed |
| `job_url` | Application link |
| `source_website` | `predoc.org` or `nber.org` |
| `duration` | Duration if listed |
| `description` | Combined metadata summary |
| `employment_type` | If listed |
| `salary` | If listed |
| `visa_sponsorship` | Visa info if listed |
| `dedup_key` | Stable deduplication key |
| `first_seen` | ISO timestamp when first discovered |
| `last_seen` | ISO timestamp from latest scrape |

---

## Error Handling

- **HTTP retries:** Exponential backoff (3 attempts by default)
- **Timeouts:** 60 seconds per request
- **SSL fallback:** urllib fallback if certificate store is incomplete
- **Per-source isolation:** One scraper failing does not stop the other
- **Layout changes:** Logged as warnings/errors; partial results still saved
- **Logging:** Console + rotating file at `logs/scraper.log`

---

## License

MIT — use freely for personal predoc job tracking.
