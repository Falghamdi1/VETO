# Pushing VETO to GitHub — step by step

You have Git nowhere near as scary as the Azure CLI was. Two paths below —
pick **Path A (GitHub Desktop)** if you've never used git; it's all clicks.

---

## Before you push — one cleanup

Make sure your secrets and junk don't get uploaded. The repo already has a
`.gitignore` that excludes `.env` and `__pycache__`. Double-check you do NOT
have a `.env` file with real keys you're about to commit. If you used plain
environment variables (the `$env:...` lines) and never made a `.env` file,
you're fine.

Also paste your demo video link into two files first:
- `demo/demo_video_link.md`
- the top of `README.md` (under the one-liner)

---

## Path A — GitHub Desktop (easiest, all clicks)

1. Download GitHub Desktop from **desktop.github.com**, install, sign in with
   your GitHub account (make one free at github.com if needed).
2. **File → Add Local Repository** → choose your `veto` folder.
   - If it says "this isn't a git repository," click **"create a repository"**
     on that same dialog. Accept the defaults.
3. You'll see all your files listed as changes. In the bottom-left, type a
   summary like `Initial commit — VETO commit gate` and click
   **Commit to main**.
4. Click **Publish repository** (top bar). Untick "Keep this code private" if
   the hackathon requires a public repo (most do — check the rules). Click
   **Publish**.
5. Done. Click **View on GitHub** to get the URL — that's your submission link.

To update later: make your change, GitHub Desktop shows it, write a summary,
**Commit**, then **Push origin**.

---

## Path B — command line (if you prefer the terminal)

In your `veto` folder, in the terminal:

```bash
git init
git add .
git commit -m "Initial commit — VETO commit gate for autonomous analytics"
```

Then create an empty repo on github.com (the **+** top-right → New repository,
name it `veto`, don't add a README, click Create). Copy the URL it shows, then:

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/veto.git
git push -u origin main
```

If it asks you to log in, GitHub will pop a browser auth window. After that,
future pushes are just:

```bash
git add .
git commit -m "what changed"
git push
```

---

## What to put in the submission form

- **Project title:** VETO — The Commit Gate for Autonomous Analytics
- **Track:** Reasoning Agents (Microsoft Foundry)
- **Repository:** your GitHub URL from above
- **Video:** your unlisted YouTube / Loom link
- **Description:** paste the full description (in `README.md`)

Submit with margin — hours before the Pacific deadline, not minutes.
