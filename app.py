from flask import Flask, request, send_file, render_template_string, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os, json, re
from datetime import datetime

app = Flask(__name__)
CORS(app)

try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT_REG  = 'DejaVuSans'
    FONT_BOLD = 'DejaVuSans-Bold'
except:
    FONT_REG  = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

HC_RED   = colors.HexColor("#c22126")
HC_DARK  = colors.HexColor("#000000")
HC_MID   = colors.HexColor("#333333")
HC_GREEN = colors.HexColor("#1a7a3a")
HC_AMBER = colors.HexColor("#c47000")

PAGE_W, PAGE_H = A4
MARGIN  = 8 * mm
LABEL_W = (PAGE_W - 2 * MARGIN) / 2
LABEL_H = (PAGE_H - 2 * MARGIN) / 2
LOGO    = os.path.join(os.path.dirname(__file__), "logo.png")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    history = history[:50]  # keep last 50
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)


def wrap_text(text, max_chars=46):
    if len(text) <= max_chars:
        return [text]
    split = text[:max_chars].rfind(" ")
    if split == -1:
        split = max_chars
    return [text[:split].strip(), text[split:].strip()]


def draw_label(c, order, x, y):
    pad = 5*mm; lw = LABEL_W; lh = LABEL_H; border = 2*mm

    c.setFillColor(colors.white)
    c.roundRect(x+border, y+border, lw-2*border, lh-2*border, 2*mm, fill=1, stroke=0)
    c.setFillColor(HC_RED)
    c.rect(x+border, y+lh-border-1.5*mm, lw-2*border, 1.5*mm, fill=1, stroke=0)

    logo_h = 10*mm; logo_x = x+border+pad
    logo_y = y+lh-border-1.5*mm-logo_h-2*mm
    if os.path.exists(LOGO):
        c.drawImage(LOGO, logo_x, logo_y, width=10*mm, height=logo_h,
                    preserveAspectRatio=True, mask='auto')

    c.setFillColor(HC_DARK); c.setFont(FONT_BOLD, 7.5)
    c.drawRightString(x+lw-border-pad, logo_y+3*mm, order["order_id"])

    cur_y = logo_y - 3*mm
    c.setStrokeColor(colors.HexColor("#aaaaaa")); c.setLineWidth(0.6)
    c.line(x+border+pad, cur_y, x+lw-border-pad, cur_y); cur_y -= 4.5*mm

    c.setFillColor(HC_RED); c.setFont(FONT_BOLD, 6.5)
    c.drawString(x+border+pad, cur_y, "SHIP TO"); cur_y -= 4.5*mm
    c.setFillColor(HC_DARK); c.setFont(FONT_BOLD, 11)
    c.drawString(x+border+pad, cur_y, order["ship_to"]); cur_y -= 5.5*mm

    c.setFont(FONT_REG, 8.5); c.setFillColor(HC_DARK)
    for line in wrap_text(order["address"], 50):
        c.drawString(x+border+pad, cur_y, line); cur_y -= 4*mm
    c.drawString(x+border+pad, cur_y, order["city_pin"]); cur_y -= 4*mm
    c.setFillColor(HC_MID); c.setFont(FONT_REG, 8)
    c.drawString(x+border+pad, cur_y, "Ph: " + order["phone"]); cur_y -= 5.5*mm

    c.setStrokeColor(colors.HexColor("#aaaaaa")); c.setLineWidth(0.6)
    c.line(x+border+pad, cur_y+1.5*mm, x+lw-border-pad, cur_y+1.5*mm); cur_y -= 4*mm

    c.setFillColor(HC_RED); c.setFont(FONT_BOLD, 6.5)
    c.drawString(x+border+pad, cur_y, "ITEM"); cur_y -= 4.5*mm
    c.setFillColor(HC_DARK); c.setFont(FONT_BOLD, 9)
    for line in wrap_text(order["name"], 46):
        c.drawString(x+border+pad, cur_y, line); cur_y -= 4.5*mm

    cur_y -= 1*mm
    badge_h = 6*mm; badge_w = 16*mm
    c.setStrokeColor(HC_RED); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(x+border+pad, cur_y-mm, badge_w, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_RED); c.setFont(FONT_BOLD, 8)
    c.drawCentredString(x+border+pad+badge_w/2, cur_y+1.5*mm, order["size"])

    fx = x+border+pad+badge_w+3*mm
    c.setStrokeColor(HC_AMBER); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(fx, cur_y-mm, 18*mm, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_AMBER); c.setFont(FONT_BOLD, 7.5)
    c.drawCentredString(fx+9*mm, cur_y+1.5*mm, "FRAGILE")

    px = x+lw-border-pad-18*mm
    c.setStrokeColor(HC_GREEN); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(px, cur_y-mm, 18*mm, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_GREEN); c.setFont(FONT_BOLD, 7.5)
    c.drawCentredString(px+9*mm, cur_y+1.5*mm, "PREPAID")

    cur_y -= 9*mm
    c.setFillColor(HC_MID); c.setFont(FONT_REG, 7)
    c.drawString(x+border+pad, cur_y, f"Carrier: {order.get('carrier', 'Tirupati')}"); cur_y -= 5*mm

    bh = 18*mm; bw = lw-2*border-2*pad
    bx = x+border+pad; by = cur_y-bh
    c.setStrokeColor(colors.HexColor("#999999")); c.setLineWidth(0.6); c.setDash(3,3)
    c.rect(bx, by, bw, bh, fill=0, stroke=1); c.setDash()
    c.setFillColor(colors.HexColor("#bbbbbb")); c.setFont(FONT_REG, 6)
    c.drawCentredString(bx+bw/2, by+bh/2+mm, "AFFIX COURIER BARCODE HERE")
    c.setFont(FONT_REG, 5.5)
    c.drawCentredString(bx+bw/2, by+bh/2-3*mm, "Tirupati / Shipmozo")

    fh = 13*mm; fy = y+border
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.roundRect(x+border, fy, lw-2*border, fh, 2*mm, fill=1, stroke=0)
    c.rect(x+border, fy+fh-2*mm, lw-2*border, 2*mm, fill=1, stroke=0)
    c.setFillColor(HC_RED); c.rect(x+border, fy, 1.5*mm, fh, fill=1, stroke=0)
    c.setFillColor(HC_DARK); c.setFont(FONT_BOLD, 6)
    ry = fy+fh-4*mm
    c.drawString(x+border+4*mm, ry, "RETURN TO:"); ry -= 3.2*mm
    c.setFont(FONT_REG, 6.2); c.setFillColor(HC_MID)
    for line in ["HUSTLE CULTURE  |  hustleculture.co.in",
                 "12A Mandeville Garden, Flat 3D, 3rd Floor, Ballygunge",
                 "Kolkata - 700019, West Bengal  |  Ph: 6289021789"]:
        c.drawString(x+border+4*mm, ry, line); ry -= 3*mm
    c.setStrokeColor(colors.HexColor("#888888")); c.setLineWidth(0.8)
    c.roundRect(x+border, y+border, lw-2*border, lh-2*border, 2*mm, fill=0, stroke=1)


HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HC Label Generator</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --red: #c22126; --red-dark: #9e1a1e; --red-light: #fdf2f2;
  --green: #1a7a3a; --amber: #c47000;
  --black: #0d0d0d; --mid: #333; --grey: #777;
  --border: #e4e4e4; --bg: #f2f1ef; --white: #fff; --beige: #fcf8c8;
  --sidebar: #1a1a1a; --sidebar-w: 220px;
  --mono: 'DM Mono', monospace; --sans: 'DM Sans', sans-serif;
}
body { font-family: var(--sans); background: var(--bg); min-height: 100vh; display: flex; }

/* ── SIDEBAR */
.sidebar {
  width: var(--sidebar-w); min-height: 100vh; background: var(--sidebar);
  display: flex; flex-direction: column; flex-shrink: 0;
  position: fixed; left: 0; top: 0; bottom: 0; z-index: 50;
}
.sb-logo {
  padding: 20px 18px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}
.sb-logo-pill {
  background: var(--beige); color: var(--red); font-weight: 700;
  font-size: 12px; letter-spacing: 0.06em; padding: 4px 9px; border-radius: 5px;
  display: inline-block; margin-bottom: 6px;
}
.sb-logo-sub { color: rgba(255,255,255,0.35); font-size: 10px; letter-spacing: 0.1em; font-family: var(--mono); }

.sb-section { padding: 16px 12px 8px; }
.sb-section-label { font-size: 9px; font-weight: 700; letter-spacing: 0.12em; color: rgba(255,255,255,0.25); font-family: var(--mono); padding: 0 6px; margin-bottom: 6px; }
.sb-nav-btn {
  display: flex; align-items: center; gap: 9px; width: 100%;
  padding: 9px 10px; border-radius: 7px; border: none; cursor: pointer;
  font-family: var(--sans); font-size: 13px; font-weight: 500;
  color: rgba(255,255,255,0.6); background: transparent;
  transition: all 0.15s; text-align: left;
}
.sb-nav-btn:hover { background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.9); }
.sb-nav-btn.active { background: rgba(194,33,38,0.2); color: white; }
.sb-nav-btn .ico { font-size: 15px; width: 18px; text-align: center; }

.sb-history { flex: 1; overflow-y: auto; padding: 0 12px 16px; }
.history-item {
  padding: 9px 10px; border-radius: 7px; cursor: pointer;
  transition: background 0.15s; margin-bottom: 2px;
}
.history-item:hover { background: rgba(255,255,255,0.06); }
.hi-date { font-size: 10px; color: rgba(255,255,255,0.3); font-family: var(--mono); margin-bottom: 2px; }
.hi-label { font-size: 12px; color: rgba(255,255,255,0.6); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hi-count { font-size: 10px; color: rgba(255,255,255,0.25); margin-top: 1px; }
.no-history { padding: 10px; color: rgba(255,255,255,0.2); font-size: 12px; font-style: italic; }

/* ── MAIN */
.main-wrap { margin-left: var(--sidebar-w); flex: 1; display: flex; flex-direction: column; min-height: 100vh; }

header {
  background: var(--white); border-bottom: 1px solid var(--border);
  height: 56px; display: flex; align-items: center; padding: 0 32px;
  position: sticky; top: 0; z-index: 40;
}
.h-title { font-size: 15px; font-weight: 700; color: var(--black); }
.h-sub { font-size: 12px; color: var(--grey); margin-left: 10px; }

main { padding: 32px 32px 80px; max-width: 680px; }

/* ── ORDER CARDS */
.order-card {
  background: var(--white); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 18px 20px; margin-bottom: 10px;
  transition: border-color 0.2s;
}
.order-card:focus-within { border-color: rgba(194,33,38,0.3); }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.card-num { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: #bbb; font-family: var(--mono); }
.remove-btn { background: none; border: none; cursor: pointer; color: #ddd; font-size: 18px; padding: 0 2px; transition: color 0.15s; }
.remove-btn:hover { color: var(--red); }

.fields { display: flex; flex-direction: column; gap: 10px; }
.field-row { display: grid; gap: 10px; }
.field-row.two { grid-template-columns: 1fr 1fr; }
.field { display: flex; flex-direction: column; gap: 5px; }
.fl { font-size: 10px; font-weight: 700; letter-spacing: 0.09em; color: #bbb; font-family: var(--mono); }
input, textarea, select {
  border: 1px solid var(--border); border-radius: 7px;
  padding: 10px 12px; font-size: 13.5px; color: var(--black);
  font-family: var(--sans); outline: none; background: #fafafa;
  transition: border-color 0.15s; width: 100%;
}
input:focus, textarea:focus, select:focus { border-color: var(--red); background: var(--white); box-shadow: 0 0 0 3px rgba(194,33,38,0.06); }
textarea { resize: none; height: 80px; line-height: 1.6; }
select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23999' d='M6 8L1 3h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 32px; cursor: pointer; }

.custom-carrier { margin-top: 6px; display: none; }
.custom-carrier.show { display: block; }

.card-footer { display: flex; gap: 6px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
.badge { font-size: 10px; font-weight: 700; letter-spacing: 0.07em; padding: 3px 9px; border-radius: 20px; }
.b-red { border: 1px solid var(--red); color: var(--red); }
.b-green { border: 1px solid var(--green); color: var(--green); }
.b-amber { border: 1px solid var(--amber); color: var(--amber); }

/* ── BOTTOM ACTIONS */
.add-btn {
  width: 100%; padding: 12px; background: transparent;
  border: 1.5px dashed #d8d8d8; border-radius: 10px;
  cursor: pointer; color: #bbb; font-size: 12px; font-weight: 700;
  letter-spacing: 0.07em; transition: all 0.15s; margin-bottom: 20px;
  font-family: var(--sans);
}
.add-btn:hover { border-color: var(--red); color: var(--red); }

.error-box { background: var(--red-light); border: 1px solid rgba(194,33,38,0.2); border-radius: 8px; padding: 11px 14px; color: var(--red); font-size: 13px; margin-bottom: 14px; display: none; }

.gen-btn {
  width: 100%; padding: 16px; background: var(--red); border: none;
  border-radius: 10px; cursor: pointer; font-family: var(--sans);
  font-size: 14px; font-weight: 700; color: white; letter-spacing: 0.06em;
  transition: all 0.2s; box-shadow: 0 4px 16px rgba(194,33,38,0.25);
}
.gen-btn:hover { background: var(--red-dark); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(194,33,38,0.3); }
.gen-btn:disabled { background: #ccc; box-shadow: none; cursor: not-allowed; transform: none; }
.gen-btn.ok { background: var(--green); box-shadow: 0 4px 16px rgba(26,122,58,0.25); }
</style>
</head>
<body>

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sb-logo">
    <div class="sb-logo-pill">HUSTLE</div>
    <div class="sb-logo-sub">LABEL GENERATOR</div>
  </div>

  <div class="sb-section">
    <div class="sb-section-label">TOOLS</div>
    <button class="sb-nav-btn active" onclick="showCreator()">
      <span class="ico">✦</span> Label Creator
    </button>
  </div>

  <div class="sb-section">
    <div class="sb-section-label">HISTORY</div>
  </div>
  <div class="sb-history" id="sb-history">
    <div class="no-history">No labels yet</div>
  </div>
</aside>

<!-- MAIN -->
<div class="main-wrap">
  <header>
    <span class="h-title">Label Creator</span>
    <span class="h-sub">4 labels per A4 · Tirupati · PREPAID</span>
  </header>

  <main>
    <div id="cards"></div>
    <button class="add-btn" onclick="addCard()">+ ADD ANOTHER ORDER</button>
    <div class="error-box" id="err"></div>
    <button class="gen-btn" id="gbtn" onclick="generate()">GENERATE PDF · <span id="lcount">1</span> LABEL</button>
  </main>
</div>

<script>
let cardCount = 0;
let history = JSON.parse(localStorage.getItem('hc_label_history') || '[]');

function addCard(data) {
  const i = cardCount++;
  const d = data || {};
  const el = document.createElement('div');
  el.className = 'order-card';
  el.id = 'card-' + i;
  el.innerHTML = `
    <div class="card-header">
      <span class="card-num" id="cn-${i}">ORDER 1</span>
      <button class="remove-btn" onclick="removeCard(${i})">×</button>
    </div>
    <div class="fields">
      <div class="field-row two">
        <div class="field">
          <span class="fl">ORDER ID *</span>
          <input type="text" placeholder="#10001" value="${d.order_id||''}" data-f="order_id">
        </div>
        <div class="field">
          <span class="fl">SIZE</span>
          <input type="text" placeholder="UK 9 / FS / One Size" value="${d.size||''}" data-f="size">
        </div>
      </div>
      <div class="field">
        <span class="fl">PRODUCT NAME *</span>
        <input type="text" placeholder="e.g. New Balance 9060 Olivine" value="${d.name||''}" data-f="name">
      </div>
      <div class="field">
        <span class="fl">RECIPIENT — paste name, address, phone, city &amp; pincode *</span>
        <textarea placeholder="e.g. Rahul Sharma, 12 MG Road, Koramangala, Bangalore 560034, +91 98765 43210" data-f="raw_address">${d.raw_address||''}</textarea>
      </div>
      <div class="field">
        <span class="fl">CARRIER</span>
        <select data-f="carrier" onchange="toggleCustom(this, ${i})">
          <option value="Tirupati" ${(!d.carrier||d.carrier==='Tirupati')?'selected':''}>Tirupati</option>
          <option value="Tirupati Surface" ${d.carrier==='Tirupati Surface'?'selected':''}>Tirupati Surface</option>
          <option value="Shipmozo" ${d.carrier==='Shipmozo'?'selected':''}>Shipmozo</option>
          <option value="other" ${(d.carrier&&d.carrier!=='Tirupati'&&d.carrier!=='Tirupati Surface'&&d.carrier!=='Shipmozo')?'selected':''}>Other (type below)</option>
        </select>
        <input type="text" class="custom-carrier ${(d.carrier&&d.carrier!=='Tirupati'&&d.carrier!=='Tirupati Surface'&&d.carrier!=='Shipmozo')?'show':''}" id="custom-${i}" placeholder="Enter carrier name" value="${(d.carrier&&d.carrier!=='Tirupati'&&d.carrier!=='Tirupati Surface'&&d.carrier!=='Shipmozo')?d.carrier:''}" data-f="custom_carrier">
      </div>
    </div>
    <div class="card-footer">
      <span class="badge b-red" id="carrier-badge-${i}">Tirupati</span>
      <span class="badge b-green">PREPAID</span>
      <span class="badge b-amber">FRAGILE</span>
    </div>
  `;
  document.getElementById('cards').appendChild(el);
  updateNums();
}

function toggleCustom(sel, i) {
  const custom = document.getElementById('custom-' + i);
  const badge = document.getElementById('carrier-badge-' + i);
  if (sel.value === 'other') {
    custom.classList.add('show');
    custom.focus();
  } else {
    custom.classList.remove('show');
    badge.textContent = sel.value;
  }
}

function removeCard(i) {
  document.getElementById('card-' + i)?.remove();
  updateNums();
  if (document.querySelectorAll('.order-card').length === 0) addCard();
}

function updateNums() {
  const cards = document.querySelectorAll('.order-card');
  cards.forEach((c, idx) => {
    const cn = c.querySelector('[id^="cn-"]');
    if (cn) cn.textContent = 'ORDER ' + (idx+1) + (cards.length > 1 ? ' / ' + cards.length : '');
  });
  const n = cards.length;
  document.getElementById('lcount').textContent = n + ' LABEL' + (n!==1?'S':'');
}

function parseRawAddress(raw) {
  const clean = raw.trim();
  const phoneMatch = clean.match(/(\+?91[\s\-]?\d{5}[\s\-]?\d{5}|\+?\d{10,12})/);
  const phone = phoneMatch ? phoneMatch[1].trim() : '';
  const pinMatch = clean.match(/\b(\d{6})\b/);
  const pincode = pinMatch ? pinMatch[1] : '';

  let rest = clean;
  if (phone) rest = rest.replace(phone, '').trim();

  const parts = rest.split(',').map(s => s.trim()).filter(Boolean);
  const ship_to = parts[0] || '';
  const city_pin_parts = parts.filter(p => p.match(/\d{6}/) || p.match(/^\d{6}$/));
  let city_pin = '';
  if (pincode) {
    const cityIdx = parts.findIndex(p => p.includes(pincode));
    if (cityIdx > 0) {
      city_pin = parts.slice(Math.max(0, cityIdx-1), cityIdx+1).join(', ').replace(/\s+/g,' ').trim();
    } else {
      city_pin = parts.slice(-2).join(', ');
    }
    city_pin = city_pin.replace(/India\s*$/i,'').replace(/\s+/g,' ').trim().replace(/,\s*$/,'');
  }
  const address_parts = parts.slice(1, parts.length - (pincode ? 2 : 0));
  const address = address_parts.join(', ').replace(/India\s*$/i,'').trim();

  return { ship_to, address, city_pin, phone };
}

function getOrders() {
  return Array.from(document.querySelectorAll('.order-card')).map(card => {
    const o = {};
    card.querySelectorAll('[data-f]').forEach(el => o[el.dataset.f] = el.value.trim());
    const carrier_sel = card.querySelector('select[data-f="carrier"]');
    const custom = card.querySelector('input[data-f="custom_carrier"]');
    o.carrier = carrier_sel.value === 'other' ? (custom?.value.trim() || 'Tirupati') : carrier_sel.value;
    const parsed = parseRawAddress(o.raw_address || '');
    o.ship_to = parsed.ship_to;
    o.address = parsed.address;
    o.city_pin = parsed.city_pin;
    o.phone = parsed.phone;
    o.payment = 'PREPAID';
    return o;
  });
}

function renderHistory() {
  const sb = document.getElementById('sb-history');
  if (!history.length) { sb.innerHTML = '<div class="no-history">No labels yet</div>'; return; }
  sb.innerHTML = history.map((h, i) => `
    <div class="history-item" onclick="redownload(${i})">
      <div class="hi-date">${h.date}</div>
      <div class="hi-label">${h.label}</div>
      <div class="hi-count">${h.count} label${h.count!==1?'s':''}</div>
    </div>
  `).join('');
}

function redownload(i) {
  const h = history[i];
  if (!h || !h.orders) return;
  generatePDF(h.orders, h.filename);
}

async function generatePDF(orders, filename) {
  const res = await fetch('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ orders })
  });
  if (!res.ok) return;
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename || 'HC_Labels.pdf';
  a.click();
}

async function generate() {
  document.getElementById('err').style.display = 'none';
  const orders = getOrders();
  const bad = orders.filter(o => !o.order_id || !o.name || !o.ship_to);
  if (bad.length) {
    document.getElementById('err').textContent = 'Fill in Order ID, Product Name, and Recipient for every order.';
    document.getElementById('err').style.display = 'block';
    return;
  }
  const btn = document.getElementById('gbtn');
  btn.disabled = true; btn.textContent = 'GENERATING...';

  try {
    const filename = 'HC_Labels_' + new Date().toISOString().slice(0,10) + '.pdf';
    await generatePDF(orders, filename);

    // Save to history
    const now = new Date();
    const entry = {
      date: now.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' }),
      label: orders.map(o => o.order_id).join(', '),
      count: orders.length,
      filename,
      orders
    };
    history.unshift(entry);
    if (history.length > 50) history = history.slice(0,50);
    localStorage.setItem('hc_label_history', JSON.stringify(history));
    renderHistory();

    btn.classList.add('ok'); btn.textContent = '✓ PDF DOWNLOADED';
    setTimeout(() => { btn.classList.remove('ok'); btn.disabled=false; updateNums(); }, 3000);
  } catch(e) {
    document.getElementById('err').textContent = 'Generation failed. Try again.';
    document.getElementById('err').style.display = 'block';
    btn.disabled = false; updateNums();
  }
}

function showCreator() {
  document.querySelector('.sb-nav-btn').classList.add('active');
}

// Init
addCard();
renderHistory();
</script>
</body>
</html>'''


@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/generate', methods=['POST'])
def generate():
    orders = request.json.get('orders', [])
    if not orders:
        return jsonify({'error': 'No orders'}), 400
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    positions = [
        (MARGIN, MARGIN + LABEL_H), (MARGIN + LABEL_W, MARGIN + LABEL_H),
        (MARGIN, MARGIN), (MARGIN + LABEL_W, MARGIN),
    ]
    for i, order in enumerate(orders):
        if i % 4 == 0 and i != 0:
            c.showPage()
        draw_label(c, order, *positions[i % 4])
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name='hustle_culture_labels.pdf')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
