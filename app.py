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

# ── Fonts
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT_REG  = 'DejaVuSans'
    FONT_BOLD = 'DejaVuSans-Bold'
except:
    FONT_REG  = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

# ── Brand
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

    # Size
    c.setStrokeColor(HC_RED); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(x+border+pad, cur_y-mm, badge_w, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_RED); c.setFont(FONT_BOLD, 8)
    c.drawCentredString(x+border+pad+badge_w/2, cur_y+1.5*mm, order["size"])

    # FRAGILE
    fx = x+border+pad+badge_w+3*mm
    c.setStrokeColor(HC_AMBER); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(fx, cur_y-mm, 18*mm, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_AMBER); c.setFont(FONT_BOLD, 7.5)
    c.drawCentredString(fx+9*mm, cur_y+1.5*mm, "FRAGILE")

    # PREPAID
    px = x+lw-border-pad-18*mm
    c.setStrokeColor(HC_GREEN); c.setFillColor(colors.white); c.setLineWidth(1)
    c.roundRect(px, cur_y-mm, 18*mm, badge_h, 1.5*mm, fill=1, stroke=1)
    c.setFillColor(HC_GREEN); c.setFont(FONT_BOLD, 7.5)
    c.drawCentredString(px+9*mm, cur_y+1.5*mm, order.get("payment", "PREPAID"))

    cur_y -= 9*mm
    c.setFillColor(HC_MID); c.setFont(FONT_REG, 7)
    c.drawString(x+border+pad, cur_y, f"Carrier: {order.get('carrier', 'Tirupati')}"); cur_y -= 5*mm

    # Barcode box
    bh = 18*mm; bw = lw-2*border-2*pad
    bx = x+border+pad; by = cur_y-bh
    c.setStrokeColor(colors.HexColor("#999999")); c.setLineWidth(0.6); c.setDash(3,3)
    c.rect(bx, by, bw, bh, fill=0, stroke=1); c.setDash()
    c.setFillColor(colors.HexColor("#bbbbbb")); c.setFont(FONT_REG, 6)
    c.drawCentredString(bx+bw/2, by+bh/2+mm, "AFFIX COURIER BARCODE HERE")
    c.setFont(FONT_REG, 5.5)
    c.drawCentredString(bx+bw/2, by+bh/2-3*mm, "Tirupati / Shipmozo")

    # Footer
    fh = 13*mm; fy = y+border
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.roundRect(x+border, fy, lw-2*border, fh, 2*mm, fill=1, stroke=0)
    c.rect(x+border, fy+fh-2*mm, lw-2*border, 2*mm, fill=1, stroke=0)
    c.setFillColor(HC_RED); c.rect(x+border, fy, 1.5*mm, fh, fill=1, stroke=0)
    c.setFillColor(HC_DARK); c.setFont(FONT_BOLD, 6)
    ry = fy+fh-4*mm
    c.drawString(x+border+4*mm, ry, "RETURN TO:"); ry -= 3.2*mm
    c.setFont(FONT_REG, 6.2); c.setFillColor(HC_MID)
    for line in [
        "HUSTLE CULTURE  |  hustleculture.co.in",
        "12A Mandeville Garden, Flat 3D, 3rd Floor, Ballygunge",
        "Kolkata - 700019, West Bengal  |  Ph: 6289021789"
    ]:
        c.drawString(x+border+4*mm, ry, line); ry -= 3*mm

    c.setStrokeColor(colors.HexColor("#888888")); c.setLineWidth(0.8)
    c.roundRect(x+border, y+border, lw-2*border, lh-2*border, 2*mm, fill=0, stroke=1)


# ── HTML Frontend
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hustle Culture · Label Generator</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; background: #f4f4f2; min-height: 100vh; }

  .header { background: #c22126; padding: 0 24px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 12px rgba(194,33,38,0.25); }
  .header-inner { max-width: 720px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; height: 56px; }
  .logo-chip { background: #fcf8c8; border-radius: 4px; padding: 4px 9px; font-weight: 900; font-size: 13px; letter-spacing: 0.04em; color: #c22126; }
  .header-title { color: rgba(255,255,255,0.65); font-size: 12px; letter-spacing: 0.1em; font-weight: 600; margin-left: 12px; }
  .header-tag { color: rgba(255,255,255,0.45); font-size: 11px; }

  .body { max-width: 720px; margin: 0 auto; padding: 28px 20px 80px; }
  .hint { color: #777; font-size: 13px; margin-bottom: 24px; line-height: 1.5; }

  .card { background: #fff; border: 1px solid #e8e8e8; border-left: 3px solid #c22126; border-radius: 8px; padding: 20px; margin-bottom: 12px; }
  .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .card-num { font-family: monospace; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: #aaa; }
  .remove-btn { background: none; border: none; cursor: pointer; color: #ccc; font-size: 22px; line-height: 1; padding: 0 4px; transition: color 0.15s; }
  .remove-btn:hover { color: #c22126; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .span2 { grid-column: 1 / -1; }
  label { display: block; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: #999; margin-bottom: 5px; }
  input { width: 100%; border: 1px solid #e2e2e2; border-radius: 5px; padding: 9px 10px; font-size: 13px; color: #111; font-family: inherit; outline: none; background: #fafafa; transition: border-color 0.15s; }
  input:focus { border-color: #c22126; background: #fff; }

  .tags { display: flex; gap: 6px; margin-top: 14px; flex-wrap: wrap; }
  .tag { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; padding: 3px 9px; border-radius: 20px; background: #fff; }

  .add-btn { width: 100%; padding: 13px; background: transparent; border: 1.5px dashed #d0d0d0; border-radius: 8px; cursor: pointer; color: #bbb; font-size: 12px; font-weight: 700; letter-spacing: 0.07em; transition: all 0.15s; margin-bottom: 20px; font-family: inherit; }
  .add-btn:hover { border-color: #c22126; color: #c22126; }

  .gen-btn { width: 100%; padding: 16px; background: #c22126; border: none; border-radius: 8px; cursor: pointer; color: #fff; font-size: 13px; font-weight: 700; letter-spacing: 0.1em; transition: background 0.2s; box-shadow: 0 4px 14px rgba(194,33,38,0.3); font-family: inherit; }
  .gen-btn:hover { background: #a81b20; }
  .gen-btn:disabled { background: #ccc; box-shadow: none; cursor: not-allowed; }
  .gen-btn.success { background: #1a7a3a; box-shadow: 0 4px 14px rgba(26,122,58,0.3); }

  .error-box { background: #fff3f3; border: 1px solid #f5c0c0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; color: #c22126; font-size: 13px; display: none; }
  .hint-small { text-align: center; color: #bbb; font-size: 11px; margin-top: 8px; }
  .footer { text-align: center; color: #ccc; font-size: 11px; margin-top: 40px; }
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div style="display:flex;align-items:center">
      <span class="logo-chip">HUSTLE</span>
      <span class="header-title">LABEL GENERATOR</span>
    </div>
    <span class="header-tag">Internal Ops Tool</span>
  </div>
</div>

<div class="body">
  <p class="hint">Fill in order details below. Add multiple orders — PDF will be print-ready with 4 labels per A4 page.</p>

  <div id="orders-container"></div>

  <button class="add-btn" onclick="addOrder()">+ ADD ANOTHER ORDER</button>

  <div class="error-box" id="error-box"></div>

  <button class="gen-btn" id="gen-btn" onclick="generate()">GENERATE PDF · <span id="count">1</span> LABEL</button>
  <p class="hint-small" id="hint-small" style="display:none">Fill all required fields to enable</p>

  <p class="footer">hustleculture.co.in · Ops Tool</p>
</div>

<template id="card-template">
  <div class="card" id="card-__IDX__">
    <div class="card-header">
      <span class="card-num">ORDER __NUM__ / <span class="total-count">1</span></span>
      <button class="remove-btn" onclick="removeOrder(__IDX__)">×</button>
    </div>
    <div class="grid">
      <div><label>ORDER ID *</label><input type="text" placeholder="e.g. #10001 or HSTLOFFLINE0093" data-field="order_id"></div>
      <div><label>SIZE</label><input type="text" placeholder="e.g. UK 9 / One Size / FS" data-field="size"></div>
      <div class="span2"><label>ITEM NAME *</label><input type="text" placeholder="e.g. New Balance 9060 Olivine" data-field="name"></div>
      <div><label>RECIPIENT NAME *</label><input type="text" placeholder="Full name" data-field="ship_to"></div>
      <div><label>PHONE *</label><input type="text" placeholder="+91 XXXXX XXXXX" data-field="phone"></div>
      <div class="span2"><label>ADDRESS *</label><input type="text" placeholder="Street, area, landmark" data-field="address"></div>
      <div class="span2"><label>CITY – PIN *</label><input type="text" placeholder="e.g. Mumbai, Maharashtra – 400001" data-field="city_pin"></div>
      <div><label>CARRIER</label><input type="text" placeholder="Tirupati" data-field="carrier" value="Tirupati"></div>
      <div><label>PAYMENT TYPE</label><input type="text" placeholder="PREPAID" data-field="payment" value="PREPAID"></div>
    </div>
    <div class="tags">
      <span class="tag" style="border:1px solid #555;color:#555">Tirupati</span>
      <span class="tag" style="border:1px solid #1a7a3a;color:#1a7a3a">PREPAID</span>
      <span class="tag" style="border:1px solid #c47000;color:#c47000">FRAGILE</span>
    </div>
  </div>
</template>

<script>
let orderCount = 0;
let orders = [];

function addOrder() {
  const idx = orderCount++;
  orders.push(idx);
  const tmpl = document.getElementById('card-template').innerHTML
    .replaceAll('__IDX__', idx)
    .replaceAll('__NUM__', orders.length);
  const wrapper = document.createElement('div');
  wrapper.innerHTML = tmpl;
  document.getElementById('orders-container').appendChild(wrapper.firstElementChild);
  updateUI();
}

function removeOrder(idx) {
  orders = orders.filter(i => i !== idx);
  document.getElementById('card-' + idx)?.remove();
  updateUI();
}

function updateUI() {
  const total = orders.length;
  document.querySelectorAll('.total-count').forEach(el => el.textContent = total);
  document.getElementById('count').textContent = total + ' LABEL' + (total !== 1 ? 'S' : '');
  if (total === 0) addOrder();
}

function getOrders() {
  return orders.map(idx => {
    const card = document.getElementById('card-' + idx);
    if (!card) return null;
    const data = {};
    card.querySelectorAll('[data-field]').forEach(input => {
      data[input.dataset.field] = input.value.trim();
    });
    return data;
  }).filter(Boolean);
}

function isValid(orders) {
  return orders.every(o => o.order_id && o.name && o.ship_to && o.address && o.city_pin && o.phone);
}

async function generate() {
  const btn = document.getElementById('gen-btn');
  const errorBox = document.getElementById('error-box');
  errorBox.style.display = 'none';

  const data = getOrders();
  if (!isValid(data)) {
    errorBox.textContent = 'Please fill in all required fields (marked with *).';
    errorBox.style.display = 'block';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'GENERATING...';

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orders: data })
    });

    if (!res.ok) throw new Error('Server error');

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const date = new Date().toISOString().slice(0,10);
    a.download = 'HC_Labels_' + date + '.pdf';
    a.click();
    URL.revokeObjectURL(url);

    btn.classList.add('success');
    btn.textContent = '✓ PDF DOWNLOADED';
    setTimeout(() => {
      btn.classList.remove('success');
      btn.disabled = false;
      btn.textContent = 'GENERATE PDF · ' + data.length + ' LABEL' + (data.length !== 1 ? 'S' : '');
    }, 3000);

  } catch(e) {
    errorBox.textContent = 'Failed to generate PDF. Please try again.';
    errorBox.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'GENERATE PDF · ' + data.length + ' LABEL' + (data.length !== 1 ? 'S' : '');
  }
}

// Init
addOrder();
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
        (MARGIN, MARGIN + LABEL_H),
        (MARGIN + LABEL_W, MARGIN + LABEL_H),
        (MARGIN, MARGIN),
        (MARGIN + LABEL_W, MARGIN),
    ]

    for i, order in enumerate(orders):
        if i % 4 == 0 and i != 0:
            c.showPage()
        draw_label(c, order, *positions[i % 4])

    c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name='hustle_culture_labels.pdf')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
