# Hustle Culture Label Generator

Simple web app for generating shipping labels. Built with Flask + ReportLab.

## Deploy on Railway

### Step 1 — Push to GitHub
Create a new GitHub repo and push this entire folder to it.

### Step 2 — Deploy on Railway
1. Go to railway.app → New Project → Deploy from GitHub repo
2. Select your repo
3. Railway auto-detects Python — no config needed
4. Click Deploy

### Step 3 — Get your URL
Railway gives you a public URL like:
`https://hc-label-generator.up.railway.app`

Share this with the team. Done.

---

## How it works
- Open the URL
- Fill in order details (add multiple orders in one session)
- Click Generate PDF → downloads instantly
- Print the PDF — 4 labels per A4 page

## Updating the logo
Replace `logo.png` with the new file and push to GitHub. Railway redeploys automatically.

## Files
- `app.py` — Flask backend + HTML frontend (single file, no build step)
- `requirements.txt` — Python dependencies
- `railway.toml` — Railway deployment config
- `nixpacks.toml` — Ensures DejaVu fonts are installed (fixes garbled text)
- `logo.png` — Hustle Culture logo
