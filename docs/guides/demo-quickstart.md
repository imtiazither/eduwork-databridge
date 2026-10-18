# Try the Local Demo

The demo uses fictional HR, learning, assessment, and credential records. You do not need a GitHub account, Docker, a company database, or real learner information to try it.

## Check your computer

Install Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/getting-started/installation/), and [Node.js 24 LTS](https://nodejs.org/en/download) with npm. Internet access is needed to download dependencies on the first run. Reopen your terminal after installing tools.

Open the downloaded repository folder in a terminal. In GitHub Desktop, use **Repository > Open in Terminal**. On Windows, use `python` instead of `python3` in the commands below.

```bash
python3 scripts/demo_doctor.py
```

The checker makes no changes. Each `[FIX]` item explains what is missing and how to fix it. `--json` prints the same checks for automation. The API and reviewer screen use separate local ports; `--api-port 8001 --ui-port 5174` checks alternatives when the usual ports are occupied.

## Start with one command

```bash
python3 scripts/demo.py
```

The launcher checks your tools, downloads locked dependencies, upgrades its separate database, loads fictional records, and starts the API and reviewer screen. The first run can take several minutes, depending on your connection. It opens a browser only after the database, seeded queue, and API connection have passed readiness checks.

The terminal prints an **Open:** link. Use that exact link: occupied default ports are skipped automatically. Everything binds to `127.0.0.1`, accessible on your own computer, not your company's network.

Keep the terminal open. Press **Ctrl+C** to stop both servers. Your demo notes are kept. To return later, run the same command. When dependencies are already installed and the checkout has not changed, `python3 scripts/demo.py --skip-install` skips downloading them again.

## A five-minute first visit

1. Open **Case overview** to see why records from four systems need reconciliation.
2. Select **Source checks** to inspect the fictional input files.
3. Select **Exceptions**. The connected queue contains nine deliberately missing employee-ID issues, not the 43 conditions illustrated by the static public example.
4. Open an issue, keep **Acknowledged**, enter a note such as "Asked the source owner for the missing ID," and select **Save resolution**.
5. Reload, return to **Exceptions**, and find your note in **Resolution history**. A note records a human review; it does not edit the source file or approve a record for publication.
6. Open **Identity review** to inspect uncertain record matches. Switch to **Demo viewer** to see the permission boundary.

The GitHub Pages site is a no-install, non-persistent preview. Use this local demo for saved decisions. Do not upload company, employee, student, or other personal data into the synthetic quickstart.

## Restart with fresh fictional records

Stop the launcher with Ctrl+C, then run:

```bash
python3 scripts/demo.py --reset
```

Type `RESET quickstart` when prompted. This removes only the owned synthetic workspace, including your demo notes, and reloads the fictional case. It does not reset other application databases. Automation must explicitly use `--reset --yes`; non-interactive resets otherwise fail.

## Other options and troubleshooting

- `--no-browser`: print the link without opening a browser.
- `--api-port 8001 --ui-port 5174`: select two specific ports; occupied ports fail without stopping other programs.
- `--workspace my-demo`: keep another named synthetic workspace under `var/demos/`.
- `--prepare-only`: install and prepare the data without starting servers.
- Setup failures: read `var/demos/quickstart/logs/setup.log`; server failures: read `api.log` or `ui.log` in the same folder. Correct the cause and retry.
- An interrupted initial data load: use the confirmed `--reset` command to start over.
- Workspace already in use: stop its existing launcher. After a crash, remove the named `.lock` file only after confirming neither of its servers is still running.

This is a local evaluation workflow, not a company deployment installer. For an organizational deployment, arrange authentication, backups, approved data access, and security review with your IT team; see [local deployment](../deployment/local.md).

## Where demo data lives

The quickstart workspace is `var/demos/quickstart/` inside your checkout. Its SQLite database, snapshots, exports, and logs are separate from the application's normal database and `.env` settings. The demo only reads the committed synthetic fixture. Existing company database settings are not used by this workflow.

The launcher holds a workspace lock while running, so a second launcher cannot reset the same data. A reset must target a directory carrying the demo's ownership marker; unrecognized folders and symbolic links are refused. The workspace is excluded from Git.
