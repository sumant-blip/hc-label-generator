from flask import Flask, request, send_file, render_template_string, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os, re

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


# ── SMART PARSER ──────────────────────────────────────────────────────────────

def parse_orders(raw_text):
    text = raw_text.strip()
    order_pattern = r'(?=#\d{3,}|HSTLOFFLINE\d+|OFFLINE\d*|OFFSale)'
    chunks = re.split(order_pattern, text)
    chunks = [c.strip() for c in chunks if c.strip()]
    orders = []
    for chunk in chunks:
        order = parse_single_order(chunk)
        if order:
            orders.append(order)
    return orders


def parse_single_order(chunk):
    if not chunk:
        return None

    # Extract order ID
    order_id_match = re.match(r'^(#\d+|HSTLOFFLINE\d+|OFFLINE\w*|OFFSale/[\w\-/]+)', chunk)
    if not order_id_match:
        return None
    order_id = order_id_match.group(1)
    rest = chunk[len(order_id):].strip()

    # Extract phone
    phone_match = re.search(r'(\+?91[\s\-]?\d{5}[\s\-]?\d{5}|\+?\d{10,12})', rest)
    phone = phone_match.group(1).strip() if phone_match else ''
    if phone_match:
        rest = rest[:phone_match.start()] + ' ' + rest[phone_match.end():]

    # Extract carrier
    carrier = 'Tirupati'
    carrier_match = re.search(r'(tirupati\s*surface|tirupati|shipmozo|air)', rest, re.IGNORECASE)
    if carrier_match:
        c_raw = carrier_match.group(1).lower()
        carrier = 'Tirupati Surface' if 'surface' in c_raw else c_raw.title()
        rest = rest[:carrier_match.start()] + ' ' + rest[carrier_match.end():]

    # Extract size
    size = 'One Size'
    size_match = re.search(r'\b(UK\s*[\d.]+|FS|LL|One\s*Size|\d+\s*-\s*\d+\s*Days?)\b', rest, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).strip()
        rest = rest[:size_match.start()] + ' ' + rest[size_match.end():]

    # Extract pincode
    pin_match = re.search(r'(\d{6})', rest)
    pincode = pin_match.group(1) if pin_match else ''

    # Extract state
    state_match = re.search(
        r'(Maharashtra|Karnataka|Delhi|Rajasthan|Gujarat|Tamil Nadu|Telangana|'
        r'Andhra Pradesh|West Bengal|Punjab|Haryana|Uttar Pradesh|Madhya Pradesh|'
        r'Kerala|Bihar|Jharkhand|Odisha|Chandigarh|Goa|MH|KA|DL|RJ|GJ|TN|TG|AP|WB|PB|HR|UP|MP)',
        rest, re.IGNORECASE)

    # Build city_pin
    city_pin = ''
    if pin_match:
        # Get text just before pincode as city name
        before_pin = rest[:pin_match.start()].strip(' ,')
        city_words = before_pin.split()[-3:] if before_pin else []
        city = ' '.join(city_words).strip(' ,')
        state = state_match.group(1) if state_match else ''
        city_pin = f"{city}, {state} - {pincode}".strip(' ,-')
        # Remove pincode and state from rest
        rest = rest[:pin_match.start()] + rest[pin_match.end():]
        if state_match:
            rest = re.sub(state_match.group(1), '', rest, flags=re.IGNORECASE)

    # Remove India
    rest = re.sub(r'\bIndia\b', '', rest, flags=re.IGNORECASE)
    rest = re.sub(r'\s{2,}', ' ', rest).strip(' ,')

    # Split into: product name | recipient name | address
    # Strategy: find a Title Case name pattern (First [Middle] Last)
    name_pattern = re.search(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z.]+){1,3})\s*,\s*(.+)',
        rest
    )

    product_name = ''
    recipient = ''
    address = ''

    if name_pattern:
        product_name = rest[:name_pattern.start()].strip(' ,')
        recipient = name_pattern.group(1).strip()
        address = name_pattern.group(2).strip(' ,')
    else:
        # Fallback split
        words = rest.split()
        split_at = max(2, len(words) // 3)
        product_name = ' '.join(words[:split_at])
        remaining = ' '.join(words[split_at:])
        rwords = remaining.split()
        recipient = ' '.join(rwords[:3]) if len(rwords) >= 3 else remaining
        address = ' '.join(rwords[3:]) if len(rwords) > 3 else ''

    # Clean trailing city from address if city_pin already has it
    address = re.sub(r',?\s*\d{6}\s*$', '', address).strip(' ,')

    return {
        'order_id': order_id,
        'name': product_name.strip(' ,') or 'See order',
        'size': size,
        'ship_to': recipient.strip(' ,') or 'Customer',
        'address': address.strip(' ,'),
        'city_pin': city_pin,
        'phone': phone,
        'carrier': carrier,
        'payment': 'PREPAID'
    }


# ── PDF GENERATION ─────────────────────────────────────────────────────────────

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


# ── HTML ───────────────────────────────────────────────────────────────────────

HTML = '''<!DOCTYPE html>
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
  --black: #0d0d0d; --mid: #444; --grey: #777; --border: #e4e4e4;
  --bg: #f7f6f4; --white: #fff; --beige: #fcf8c8;
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

main { max-width: 740px; margin: 0 auto; padding: 48px 24px 80px; }
h1 { font-size: 26px; font-weight: 700; margin-bottom: 8px; }
.sub { color: var(--grey); font-size: 14px; line-height: 1.6; margin-bottom: 32px; }
.sub strong { color: var(--mid); }

.input-card {
  background: var(--white); border: 1.5px solid var(--border);
  border-radius: 12px; overflow: hidden; margin-bottom: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-card:focus-within { border-color: var(--red); box-shadow: 0 0 0 3px rgba(194,33,38,0.07); }
.input-top {
  display: flex; align-items: center; gap: 8px;
  padding: 13px 16px 11px; border-bottom: 1px solid var(--border);
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--red); }
.input-top-label { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: var(--grey); font-family: var(--mono); }
textarea {
  width: 100%; min-height: 200px; padding: 16px;
  border: none; outline: none; font-family: var(--mono);
  font-size: 12.5px; color: var(--black); background: transparent;
  resize: vertical; line-height: 1.7;
}
textarea::placeholder { color: #bbb; }

.preview-wrap { display: none; margin-bottom: 24px; }
.preview-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.preview-lbl { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: var(--grey); font-family: var(--mono); }
.preview-badge { background: var(--red); color: white; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; font-family: var(--mono); }
.preview-list { display: grid; gap: 6px; }
.p-card {
  background: var(--white); border: 1px solid var(--border);
  border-left: 3px solid var(--red); border-radius: 8px;
  padding: 11px 14px; display: flex; gap: 12px; align-items: start;
}
.p-id { font-family: var(--mono); font-size: 11px; color: var(--red); white-space: nowrap; padding-top: 2px; min-width: 90px; }
.p-info { flex: 1; min-width: 0; }
.p-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 2px; }
.p-addr { font-size: 11px; color: var(--grey); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.p-size { font-family: var(--mono); font-size: 10px; background: var(--red-light); color: var(--red); padding: 3px 8px; border-radius: 4px; white-space: nowrap; font-weight: 500; align-self: flex-start; }

.error { background: var(--red-light); border: 1px solid rgba(194,33,38,0.2); border-radius: 8px; padding: 11px 14px; color: var(--red); font-size: 13px; margin-bottom: 14px; display: none; }

.btn-row { display: flex; gap: 10px; }
.btn-preview {
  padding: 14px 20px; background: var(--white); border: 1.5px solid var(--border);
  border-radius: 10px; cursor: pointer; font-family: var(--sans); font-size: 13px;
  font-weight: 600; color: var(--mid); letter-spacing: 0.03em; transition: all 0.15s; white-space: nowrap;
}
.btn-preview:hover { border-color: var(--red); color: var(--red); }
.btn-gen {
  flex: 1; padding: 14px; background: var(--red); border: none; border-radius: 10px;
  cursor: pointer; font-family: var(--sans); font-size: 13px; font-weight: 700;
  color: white; letter-spacing: 0.06em; transition: all 0.2s;
  box-shadow: 0 4px 16px rgba(194,33,38,0.28);
}
.btn-gen:hover { background: var(--red-dark); transform: translateY(-1px); }
.btn-gen:disabled { background: #ccc; box-shadow: none; cursor: not-allowed; transform: none; }
.btn-gen.ok { background: var(--green); }

footer { text-align: center; color: #bbb; font-size: 11px; margin-top: 48px; font-family: var(--mono); letter-spacing: 0.05em; }
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
  <h1>Generate shipping labels</h1>
  <p class="sub">Paste raw order data below — <strong>one or multiple orders</strong>. The system parses and generates print-ready labels automatically.</p>

  <div class="input-card">
    <div class="input-top">
      <div class="dot"></div>
      <span class="input-top-label">PASTE ORDER DATA</span>
    </div>
    <textarea id="inp" placeholder="#10001New Balance 9060 OlivineUK 9TirupatiRahul Sharma, 12 MG Road, Koramangala, 560034 Bangalore Karnataka, India, +91 98765 43210&#10;&#10;#10002Whoop 5.0 Coreknit Jet BlackFSTirupatiPriya Singh, 401 Sea View, Bandra West, 400050 Mumbai MH, +91 91234 56789"></textarea>
  </div>

  <div class="error" id="err"></div>

  <div class="preview-wrap" id="pv">
    <div class="preview-head">
      <span class="preview-lbl">PARSED — REVIEW BEFORE GENERATING</span>
      <span class="preview-badge" id="pv-count">0</span>
    </div>
    <div class="preview-list" id="pv-list"></div>
  </div>

  <div class="btn-row">
    <button class="btn-preview" onclick="preview()">Preview</button>
    <button class="btn-gen" id="gbtn" onclick="generate()">Generate PDF</button>
  </div>

  <footer>hustleculture.co.in &nbsp;·&nbsp; defaults: tirupati + prepaid</footer>
</main>

<script>
let parsed = [];

async function preview() {
  const raw = document.getElementById('inp').value.trim();
  if (!raw) return err('Paste some order data first.');
  clearErr();
  const r = await fetch('/parse', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text:raw}) });
  const d = await r.json();
  if (!d.orders?.length) return err('No orders found. Make sure order IDs start with # (e.g. #10001).');
  parsed = d.orders;
  showPreview(parsed);
}

function showPreview(orders) {
  document.getElementById('pv-count').textContent = orders.length + ' label' + (orders.length!==1?'s':'');
  document.getElementById('pv-list').innerHTML = orders.map(o => `
    <div class="p-card">
      <div class="p-id">${o.order_id}</div>
      <div class="p-info">
        <div class="p-name">${o.name}</div>
        <div class="p-addr">${o.ship_to} &middot; ${o.city_pin} &middot; ${o.phone}</div>
      </div>
      <div class="p-size">${o.size}</div>
    </div>`).join('');
  document.getElementById('pv').style.display = 'block';
}

async function generate() {
  const raw = document.getElementById('inp').value.trim();
  if (!raw) return err('Paste some order data first.');
  clearErr();
  const btn = document.getElementById('gbtn');
  btn.disabled = true; btn.textContent = 'GENERATING...';

  try {
    if (!parsed.length) {
      const r = await fetch('/parse', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text:raw}) });
      const d = await r.json();
      if (!d.orders?.length) { btn.disabled=false; btn.textContent='Generate PDF'; return err('No orders found.'); }
      parsed = d.orders;
      showPreview(parsed);
    }

    const res = await fetch('/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({orders:parsed}) });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'HC_Labels_' + new Date().toISOString().slice(0,10) + '.pdf';
    a.click();
    btn.classList.add('ok'); btn.textContent = '✓ PDF DOWNLOADED';
    setTimeout(() => { btn.classList.remove('ok'); btn.disabled=false; btn.textContent='Generate PDF'; }, 3000);
  } catch(e) {
    err('Generation failed. Try again.'); btn.disabled=false; btn.textContent='Generate PDF';
  }
}

function err(msg) { const b=document.getElementById('err'); b.textContent=msg; b.style.display='block'; }
function clearErr() { document.getElementById('err').style.display='none'; }
document.getElementById('inp').addEventListener('input', () => { parsed=[]; document.getElementById('pv').style.display='none'; });
</script>
</body>
</html>'''


@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/parse', methods=['POST'])
def parse_route():
    text = request.json.get('text', '')
    orders = parse_orders(text)
    return jsonify({'orders': orders})

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
