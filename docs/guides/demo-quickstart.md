# Try the Local Demo

The demo uses fictional HR, learning, assessment, and credential records. You do not need a GitHub account, Docker, a company database, or real learner information to try it.

## Check your computer

Install Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/getting-started/installation/), and [Node.js 24 LTS](https://nodejs.org/en/download) with npm. Internet access is needed to download dependencies on the first run. Reopen your terminal after installing tools.

Open the downloaded repository folder in a terminal. In GitHub Desktop, use **Repository > Open in Terminal**. On Windows, use `python` instead of `python3` in the commands below.

```bash
python3 scripts/demo_doctor.py
```

The checker makes no changes. Each `[FIX]` item explains what is missing and how to fix it. `--json` prints the same checks for automation. The API and reviewer screen use separate local ports; `--api-port 8001 --ui-port 5174` checks alternatives when the usual ports are occupied.

## Where demo data lives

The quickstart workspace is `var/demos/quickstart/` inside your checkout. Its SQLite database, snapshots, exports, and logs are separate from the application's normal database and `.env` settings. The demo only reads the committed synthetic fixture. Existing company database settings are not used by this workflow.

The launcher holds a workspace lock while running, so a second launcher cannot reset the same data. A reset must target a directory carrying the demo's ownership marker; unrecognized folders and symbolic links are refused. The workspace is excluded from Git.
