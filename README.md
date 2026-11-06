# TruthGuard AI

**TruthGuard AI** is a responsible media-analysis college project. It provides two local, lightweight workflows: text-style assessment for suspicious news headlines or articles, and baseline visual consistency analysis for uploaded video files. The application reports signals and uncertainty rather than claiming to prove whether content is true, false, authentic, or manipulated.

> **Responsible-use notice:** TruthGuard AI provides an automated, probabilistic assessment. It cannot guarantee that a news article is true or false, or that a video is authentic or manipulated. Always verify important information using reliable independent sources.

## Project at a glance

| Area | Implementation |
|---|---|
| Application server | Python 3 and Flask |
| Persistence | Local SQLite database created automatically on startup |
| Fake-news workflow | TF-IDF vectorisation, Logistic Regression demo model, and resilient rule-based fallback |
| Video workflow | OpenCV and NumPy metadata extraction with sampled-frame visual consistency signals |
| Client interface | Responsive HTML, CSS, and vanilla JavaScript bundled in `static/` |
| Charts and icons | Locally bundled Chart.js and Lucide browser builds under `static/vendor/` |
| External services | None. No API keys, paid APIs, frontend build tools, or large pretrained models are required. |

## Features

TruthGuard AI has six connected pages. **Overview** introduces the tool, its local-first posture, and two guided entry points. **News Scan** accepts a headline and/or article, validates length, reports a probabilistic label, confidence, risk, explanation, and text statistics. **Video Scan** accepts a supported video, validates extension and a 50 MB limit, samples frames, and displays baseline visual findings with metadata and practical previews. **Dashboard** presents live aggregates and charts from persisted scans. **History** provides safe search, filtering, deletion, and clear-history controls. **About** explains the methods, technology, and limitations in plain language.

All successful scans are persisted in SQLite. The user interface never ships pre-seeded scan totals or fabricated analysis history: dashboard totals, results, and activity values come only from records produced by completed local scans.

## Architecture

```text
Browser
  ├── Home, News, Video, Dashboard, History, and About pages
  └── JavaScript fetch requests and multipart upload handling
          │
          ▼
Flask application (app.py)
  ├── Validation and friendly JSON error responses
  ├── News detector (news_detector.py)
  ├── Video detector (video_detector.py)
  └── SQLite data access (database.py)
          │
          ▼
Local files
  ├── data/truthguard.db     SQLite scan records
  ├── models/*.joblib        compact locally-trained text model files
  └── uploads/               short-lived secure temporary video files
```

## Installation

Use Python 3.10 or newer. The dependency set is intentionally small and listed in `requirements.txt`.

```bash
git clone <your-repository-url>
cd truthguard-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows one-click setup

The exported project is self-contained: its CSS, JavaScript, icons, and chart library are all under the root `static/` directory. **No Node.js, Vite, React, Tailwind, or frontend build command is required.**

In Windows Command Prompt, double-click `run_windows.bat`, or execute:

```bat
run_windows.bat
```

In PowerShell, execute:

```powershell
.\run_windows.ps1
```

Both scripts create `.venv` if needed, install every package from `requirements.txt`, and start the Flask server. To run manually in the VS Code terminal, use `py -m pip install -r requirements.txt` followed by `py app.py`. Open `http://127.0.0.1:5000` in a browser.

## Run locally or on Replit

Start the Flask server with the command below. It binds to `0.0.0.0` and honours the `PORT` environment variable, so it is compatible with Windows, Replit, and container hosting environments.

```bash
python3 app.py
```

The default local address is `http://127.0.0.1:5000`. On Windows, `py app.py` or `python app.py` serves the same fully styled application immediately. To choose a different port, set `PORT` before launching, for example `PORT=3000 python3 app.py` on macOS/Linux. The included `.replit` file uses `python3 app.py` as its Run command.

## Analysis methods

### Fake-news text analysis

The first time it runs, `news_detector.py` creates a deliberately small local demo training corpus containing neutral reporting-style and sensational-style examples. It creates TF-IDF features from words and short phrases, trains a compact Logistic Regression classifier, and saves the vectoriser and classifier into `models/`. This process uses no downloaded dataset or model.

At scan time, the application blends the model’s class probability with transparent language signals, including sensational phrase matches, excessive punctuation, upper-case emphasis, and very short claims. It returns one of two careful labels, **Likely Reliable** or **Potentially Misleading**, along with a confidence value below 100%, a risk level, a reason, and text statistics. If model creation or loading fails, a rule-based fallback continues to provide a safe, non-crashing assessment.

The text workflow does **not** determine truth. It cannot independently inspect a claim’s source, primary evidence, publication context, omission, or intent. A “Likely Reliable” label only means the submitted wording did not trigger prominent style signals in this local baseline.

### Baseline visual video analysis

The video flow temporarily stores an allowed file with a secure generated filename, opens it with OpenCV, reads duration/FPS/resolution/frame-count metadata, and samples approximately 10–18 evenly distributed frames. For each readable sample it measures basic brightness, colour, and edge-detail variation. Those measures generate an intentionally cautious consistency score and a small set of preview thumbnails.

The result is labelled **Likely Authentic** or **Potential Deepfake**, but this is explicitly called **Baseline Visual Analysis** throughout the product. Visual variation can be caused by compression, editing, scene changes, lighting, motion, and video encoding. It is not forensic software and cannot guarantee that a video is authentic or manipulated.

When the measured baseline consistency score reaches the highest signal band, TruthGuard AI returns **Potential AI-Generated Video** with the accompanying summary, “This may be an AI-generated / Deepfake Video.” This third label is derived from the same OpenCV/NumPy frame measurements, not an external model or hardcoded demo outcome. Every video response also contains the persistent warning that the AI-assisted analysis cannot guarantee whether a video is AI-generated, manipulated, or authentic.

## Database schema

The application creates the `scans` table automatically. SQLite parameterised statements are used for inserts, history filters, deletions, and aggregation queries.

| Column | Type | Purpose |
|---|---|---|
| `id` | INTEGER | Auto-incremented primary key |
| `scan_type` | TEXT | `news` or `video` |
| `input_name` | TEXT | Headline excerpt or securely normalised original filename |
| `result` | TEXT | Responsible result label |
| `confidence` | REAL | Probabilistic score shown in the interface |
| `risk` | TEXT | `Low`, `Medium`, or `High` |
| `details` | TEXT | JSON representation of analysis metadata and explanation |
| `created_at` | TEXT | UTC ISO timestamp |

## Routes and API contract

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Overview page |
| `/news` | GET | Fake-news text scanner |
| `/api/analyze-news` | POST | Validated JSON text analysis request |
| `/video` | GET | Video upload and baseline visual analysis page |
| `/api/analyze-video` | POST | Multipart video analysis request |
| `/dashboard` | GET | Live dashboard page |
| `/api/statistics` | GET | SQLite-backed statistics and chart data |
| `/history` | GET | Scan history page |
| `/api/history` | GET | Searchable/filterable SQLite scan records |
| `/api/delete-scan` | POST | Delete one scan using its numeric ID |
| `/api/clear-history` | POST | Clear local scan history |
| `/about` | GET | Methodology, technology, and limitations page |

Analysis endpoints return structured JSON with `ok`, `scan_id`, and `analysis` keys on success. Validation and unexpected errors return a friendly `ok: false` response with an `error` message; raw Python stack traces are not sent to users.

## Security and resource controls

The application accepts only `.mp4`, `.mov`, `.avi`, and `.mkv` upload extensions. Flask enforces a 50 MB request cap; the server checks again after temporary saving. Uploaded content is never executed, uses a secure generated temporary name, and is removed after each processing attempt. Text input is capped at 12,000 combined characters. SQLite filters and deletion actions use bound parameters instead of string interpolation.

The project keeps processing deliberately lightweight. Frame sampling is capped, no background process is needed, no media byte is stored in the database, and completed request work is synchronous and cleaned up promptly.

## Testing and demo workflow

The repository contains a Python `unittest` suite, executed through the Vitest test command, that verifies text result safety, parameterised history behaviour, statistics aggregation, and successful metadata extraction from a small generated local video.

```bash
python3 -m unittest discover -s tests -v
# or, after pnpm install
pnpm test
```

For a quick demonstration, open the News Scan page and submit a neutral reporting-style example, then submit a clearly sensational, all-caps claim and compare the language signals. Next, upload a small supported video to inspect metadata, sampled-frame previews, and the baseline warning. Finally, visit Dashboard and History to see the newly completed scans drive the totals and charts.

## Project structure

```text
truthguard-ai/
├── app.py                 Flask pages, API routes, and error handling
├── database.py            SQLite initialisation, queries, and aggregate statistics
├── news_detector.py       Local demo model, fallback rules, and text statistics
├── video_detector.py      OpenCV metadata and sampled-frame consistency analysis
├── utils.py               Shared validation limits and allowed video extensions
├── requirements.txt       Lightweight Python dependencies
├── templates/             HTML page templates
├── static/                Root-level self-contained Flask frontend assets
│   ├── css/style.css       Responsive cybersecurity interface styling
│   ├── js/app.js           UI behaviour, chart rendering, and API requests
│   └── vendor/             Bundled Chart.js and Lucide browser builds
├── run_windows.bat        One-click Windows Command Prompt launcher
├── run_windows.ps1        One-click Windows PowerShell launcher
├── tests/                 Local Python tests
├── data/                  Runtime SQLite database location
├── models/                Runtime model artefact location
├── uploads/               Short-lived temporary video upload location
└── .replit                Replit Run configuration
```

## Limitations and future improvements

TruthGuard AI is a demonstration system and should be evaluated as such. Its demo training corpus is small by design, text-style cues do not establish truth, and its video analysis does not evaluate provenance, audio, face geometry, temporal synthesis artefacts, or platform metadata. The confidence score represents the internal baseline’s separation, not an objective probability of factual truth or manipulation.

Possible future improvements include an opt-in transparent larger curated dataset, source and citation analysis, robust media provenance checks, batch administration, user authentication, accessible language localisation, stronger test coverage with a broader local fixture set, and separate expert-review workflows. Any advanced version should maintain the same responsible-use disclosures and should undergo appropriate empirical evaluation before consequential use.
