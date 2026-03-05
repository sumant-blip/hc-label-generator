# Hustle Culture Label Generator — Vercel Deployment

## Overview
Fully client-side React app. No backend needed — PDF is generated in the browser using pdf-lib.
One-click deploy to Vercel.

---

## Deploy in 5 minutes

### 1. Push to GitHub
- Create a new GitHub repo (e.g. `hc-label-generator`)
- Push this entire folder to it

### 2. Deploy on Vercel
- Go to [vercel.com](https://vercel.com) → New Project
- Import your GitHub repo
- Vercel auto-detects Vite — no config needed
- Click **Deploy**

### 3. Share the link
Vercel gives you a URL like:
```
https://hc-label-generator.vercel.app
```
Share this with ops. Done.

---

## How it works
- PDF is generated entirely in the browser (no server, no data sent anywhere)
- Uses `pdf-lib` for PDF generation
- Logo is loaded from `/public/logo.png` — update this file to change the logo
- All labels default to: Carrier = Tirupati, Payment = PREPAID, FRAGILE

---

## Local development
```bash
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Updating the logo
Replace `public/logo.png` with the new logo file and redeploy (push to GitHub — Vercel auto-redeploys).

---

## Project structure
```
hc-labels-vercel/
├── public/
│   └── logo.png          # HC logo
├── src/
│   ├── App.jsx            # Main UI
│   ├── generatePDF.js     # Label PDF logic (pdf-lib)
│   └── main.jsx           # Entry point
├── index.html
├── package.json
├── vercel.json
└── vite.config.js
```
