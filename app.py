from flask import Flask, request, send_file, render_template_string, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os

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
    c.drawCentredString(px+9*mm, cur_y+1.5*mm, order.get("payment", "PREPAID"))

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
  --black: #0d0d0d; --mid: #444; --grey: #777;
  --border: #e4e4e4; --bg: #f7f6f4; --white: #fff; --beige: #fcf8c8;
  --mono: 'DM Mono', monospace; --sans: 'DM Sans', sans-serif;
}
body { font-family: var(--sans); background: var(--bg); min-height: 100vh; color: var(--black); }

header {
  background: var(--red); height: 60px; display: flex; align-items: center;
  padding: 0 32px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 20px rgba(194,33,38,0.3);
}
.logo-pill { background: var(--beige); color: var(--red); font-weight: 700; font-size: 14px; letter-spacing: 0.06em; padding: 5px 11px; border-radius: 6px; }
.hdiv { width: 1px; height: 20px; background: rgba(255,255,255,0.25); margin: 0 16px; }
.htxt { color: rgba(255,255,255,0.7); font-size: 13px; letter-spacing: 0.08em; font-weight: 500; }
.hbadge { margin-left: auto; background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.55); font-size: 10px; letter-spacing: 0.1em; padding: 4px 10px; border-radius: 20px; font-family: var(--mono); }

main { max-width: 700px; margin: 0 auto; padding: 40px 24px 80px; }
h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
.sub { color: var(--grey); font-size: 14px; line-height: 1.6; margin-bottom: 32px; }

/* ORDER CARD */
.order-card {
  background: var(--white); border: 1.5px solid var(--border);
  border-left: 4px solid var(--red); border-radius: 10px;
  padding: 20px; margin-bottom: 12px; position: relative;
}
.card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.card-num { font-family: var(--mono); font-size: 10px; font-weight: 500; color: #aaa; letter-spacing: 0.08em; }
.remove-btn { background: none; border: none; cursor: pointer; color: #ccc; font-size: 20px; line-height: 1; padding: 0 2px; transition: color 0.15s; }
.remove-btn:hover { color: var(--red); }

.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.field-row.single { grid-template-columns: 1fr; }
.field-row.triple { grid-template-columns: 2fr 1fr 1fr; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field-label { font-size: 10px; font-weight: 700; letter-spacing: 0.09em; color: #aaa; font-family: var(--mono); }
.field input, .field textarea {
  border: 1px solid var(--border); border-radius: 6px;
  padding: 9px 11px; font-size: 13px; color: var(--black);
  font-family: var(--sans); outline: none; background: #fafafa;
  transition: border-color 0.15s; width: 100%;
}
.field input:focus, .field textarea:focus { border-color: var(--red); background: var(--white); }
.field textarea { resize: none; height: 60px; line-height: 1.5; }

.tags { display: flex; gap: 6px; margin-top: 4px; }
.tag { font-size: 10px; font-weight: 700; letter-spacing: 0.07em; padding: 3px 9px; border-radius: 20px; }
.tag-red { border: 1px solid var(--red); color: var(--red); }
.tag-green { border: 1px solid var(--green); color: var(--green); }
.tag-amber { border: 1px solid var(--amber); color: var(--amber); }

/* ADD BUTTON */
.add-btn {
  width: 100%; padding: 13px; background: transparent;
  border: 1.5px dashed #d0d0d0; border-radius: 10px;
  cursor: pointer; color: #bbb; font-size: 12px; font-weight: 700;
  letter-spacing: 0.07em; transition: all 0.15s; margin-bottom: 20px;
  font-family: var(--sans);
}
.add-btn:hover { border-color: var(--red); color: var(--red); }

/* GENERATE */
.error { background: var(--red-light); border: 1px solid rgba(194,33,38,0.2); border-radius: 8px; padding: 11px 14px; color: var(--red); font-size: 13px; margin-bottom: 14px; display: none; }

.gen-btn {
  width: 100%; padding: 16px; background: var(--red); border: none;
  border-radius: 10px; cursor: pointer; font-family: var(--sans);
  font-size: 14px; font-weight: 700; color: white; letter-spacing: 0.06em;
  transition: all 0.2s; box-shadow: 0 4px 16px rgba(194,33,38,0.28);
}
.gen-btn:hover { background: var(--red-dark); transform: translateY(-1px); }
.gen-btn:disabled { background: #ccc; box-shadow: none; cursor: not-allowed; transform: none; }
.gen-btn.ok { background: var(--green); }

footer { text-align: center; color: #ccc; font-size: 11px; margin-top: 48px; font-family: var(--mono); }
</style>
</head>
<body>
<header>
  <span class="logo-pill">HUSTLE</span>
  <div class="hdiv"></div>
  <span class="htxt">LABEL GENERATOR</span>
  <span class="hbadge">INTERNAL OPS</span>
</header>

<main>
  <h1>Shipping Labels</h1>
  <p class="sub">Fill in order details below. Add as many orders as needed — PDF downloads with 4 labels per A4 page.</p>

  <div id="cards"></div>
  <button class="add-btn" onclick="addCard()">+ ADD ANOTHER ORDER</button>

  <div class="error" id="err"></div>
  <button class="gen-btn" id="gbtn" onclick="generate()">GENERATE PDF · <span id="lcount">1</span> LABEL</button>

  <footer>hustleculture.co.in · defaults: tirupati + prepaid + fragile</footer>
</main>

<script>
let count = 0;

function addCard(data) {
  const i = count++;
  const d = data || {};
  const el = document.createElement('div');
  el.className = 'order-card';
  el.id = 'card-' + i;
  el.innerHTML = `
    <div class="card-top">
      <span class="card-num" id="lbl-${i}">ORDER ${document.querySelectorAll('.order-card').length + 1}</span>
      <button class="remove-btn" onclick="removeCard(${i})">×</button>
    </div>
    <div class="field-row">
      <div class="field">
        <span class="field-label">ORDER ID *</span>
        <input type="text" placeholder="#10001 or HSTLOFFLINE0093" value="${d.order_id||''}" data-f="order_id">
      </div>
      <div class="field">
        <span class="field-label">SIZE</span>
        <input type="text" placeholder="UK 9 / FS / One Size" value="${d.size||''}" data-f="size">
      </div>
    </div>
    <div class="field-row single">
      <div class="field">
        <span class="field-label">PRODUCT NAME *</span>
        <input type="text" placeholder="e.g. New Balance 9060 Olivine" value="${d.name||''}" data-f="name">
      </div>
    </div>
    <div class="field-row">
      <div class="field">
        <span class="field-label">RECIPIENT NAME *</span>
        <input type="text" placeholder="Full name" value="${d.ship_to||''}" data-f="ship_to">
      </div>
      <div class="field">
        <span class="field-label">PHONE *</span>
        <input type="text" placeholder="+91 XXXXX XXXXX" value="${d.phone||''}" data-f="phone">
      </div>
    </div>
    <div class="field-row single">
      <div class="field">
        <span class="field-label">ADDRESS *</span>
        <textarea placeholder="Street, area, landmark" data-f="address">${d.address||''}</textarea>
      </div>
    </div>
    <div class="field-row">
      <div class="field">
        <span class="field-label">CITY – PIN *</span>
        <input type="text" placeholder="Mumbai, Maharashtra – 400001" value="${d.city_pin||''}" data-f="city_pin">
      </div>
      <div class="field">
        <span class="field-label">CARRIER</span>
        <input type="text" placeholder="Tirupati" value="${d.carrier||'Tirupati'}" data-f="carrier">
      </div>
    </div>
    <div class="tags">
      <span class="tag tag-red">Tirupati</span>
      <span class="tag tag-green">PREPAID</span>
      <span class="tag tag-amber">FRAGILE</span>
    </div>
  `;
  document.getElementById('cards').appendChild(el);
  updateCount();
}

function removeCard(i) {
  document.getElementById('card-' + i)?.remove();
  updateCount();
  if (document.querySelectorAll('.order-card').length === 0) addCard();
}

function updateCount() {
  const cards = document.querySelectorAll('.order-card');
  cards.forEach((c, idx) => {
    const lbl = c.querySelector('[id^="lbl-"]');
    if (lbl) lbl.textContent = 'ORDER ' + (idx + 1) + ' / ' + cards.length;
  });
  const n = cards.length;
  document.getElementById('lcount').textContent = n + ' LABEL' + (n !== 1 ? 'S' : '');
}

function getOrders() {
  return Array.from(document.querySelectorAll('.order-card')).map(card => {
    const o = {};
    card.querySelectorAll('[data-f]').forEach(el => o[el.dataset.f] = el.value.trim());
    o.payment = 'PREPAID';
    return o;
  });
}

async function generate() {
  document.getElementById('err').style.display = 'none';
  const orders = getOrders();
  const bad = orders.filter(o => !o.order_id || !o.name || !o.ship_to || !o.phone || !o.address || !o.city_pin);
  if (bad.length) {
    document.getElementById('err').textContent = 'Please fill in all required fields (marked *) for every order.';
    document.getElementById('err').style.display = 'block';
    return;
  }
  const btn = document.getElementById('gbtn');
  btn.disabled = true; btn.textContent = 'GENERATING...';
  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orders })
    });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'HC_Labels_' + new Date().toISOString().slice(0,10) + '.pdf';
    a.click();
    btn.classList.add('ok');
    btn.textContent = '✓ PDF DOWNLOADED';
    setTimeout(() => { btn.classList.remove('ok'); btn.disabled = false; updateCount(); btn.textContent = 'GENERATE PDF · ' + orders.length + ' LABEL' + (orders.length!==1?'S':''); }, 3000);
  } catch(e) {
    document.getElementById('err').textContent = 'Generation failed. Try again.';
    document.getElementById('err').style.display = 'block';
    btn.disabled = false;
    updateCount();
  }
}

addCard();
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
