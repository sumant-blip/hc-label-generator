import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';

// ── Brand Colors (0–1 scale for pdf-lib)
const HC_RED    = rgb(0.761, 0.129, 0.149);   // #c22126
const HC_AMBER  = rgb(0.769, 0.439, 0);        // #c47000
const HC_GREEN  = rgb(0.102, 0.478, 0.227);    // #1a7a3a
const HC_DARK   = rgb(0, 0, 0);
const HC_MID    = rgb(0.2, 0.2, 0.2);
const HC_GREY   = rgb(0.53, 0.53, 0.53);
const HC_LGREY  = rgb(0.94, 0.94, 0.94);
const HC_DGREY  = rgb(0.6, 0.6, 0.6);
const WHITE     = rgb(1, 1, 1);

const A4_W = 595.28;
const A4_H = 841.89;
const MARGIN = 22.68;  // 8mm
const LABEL_W = (A4_W - 2 * MARGIN) / 2;
const LABEL_H = (A4_H - 2 * MARGIN) / 2;

const mm = 2.835; // 1mm in points

function wrapText(text, font, fontSize, maxWidth) {
  const words = text.split(' ');
  const lines = [];
  let current = '';
  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    const w = font.widthOfTextAtSize(test, fontSize);
    if (w > maxWidth && current) {
      lines.push(current);
      current = word;
    } else {
      current = test;
    }
  }
  if (current) lines.push(current);
  return lines;
}

function drawRoundRect(page, x, y, w, h, r, { fill, stroke, fillColor, strokeColor, lineWidth = 1 } = {}) {
  const { drawRectangle, drawLine } = page;
  // pdf-lib doesn't have native roundRect, so we approximate with rect + circles at corners
  if (fill && fillColor) {
    page.drawRectangle({ x: x + r, y, width: w - 2 * r, height: h, color: fillColor, borderWidth: 0 });
    page.drawRectangle({ x, y: y + r, width: w, height: h - 2 * r, color: fillColor, borderWidth: 0 });
    page.drawEllipse({ x: x + r, y: y + r, xScale: r, yScale: r, color: fillColor, borderWidth: 0 });
    page.drawEllipse({ x: x + w - r, y: y + r, xScale: r, yScale: r, color: fillColor, borderWidth: 0 });
    page.drawEllipse({ x: x + r, y: y + h - r, xScale: r, yScale: r, color: fillColor, borderWidth: 0 });
    page.drawEllipse({ x: x + w - r, y: y + h - r, xScale: r, yScale: r, color: fillColor, borderWidth: 0 });
  }
  if (stroke && strokeColor) {
    // top
    page.drawLine({ start: { x: x + r, y: y + h }, end: { x: x + w - r, y: y + h }, color: strokeColor, thickness: lineWidth });
    // bottom
    page.drawLine({ start: { x: x + r, y }, end: { x: x + w - r, y }, color: strokeColor, thickness: lineWidth });
    // left
    page.drawLine({ start: { x, y: y + r }, end: { x, y: y + h - r }, color: strokeColor, thickness: lineWidth });
    // right
    page.drawLine({ start: { x: x + w, y: y + r }, end: { x: x + w, y: y + h - r }, color: strokeColor, thickness: lineWidth });
  }
}

function badge(page, x, y, w, h, text, color, boldFont, fontSize) {
  // Outline badge
  drawRoundRect(page, x, y, w, h, 4, { fill: true, fillColor: WHITE });
  drawRoundRect(page, x, y, w, h, 4, { stroke: true, strokeColor: color, lineWidth: 0.8 });
  const tw = boldFont.widthOfTextAtSize(text, fontSize);
  page.drawText(text, { x: x + (w - tw) / 2, y: y + h / 2 - fontSize * 0.35, size: fontSize, font: boldFont, color });
}

async function drawLabel(page, order, ox, oy, logoImageEmbed, boldFont, regularFont) {
  const pad = 5 * mm;
  const border = 2 * mm;
  const lw = LABEL_W;
  const lh = LABEL_H;

  // pdf-lib Y is bottom-up, so oy is the bottom of the label cell
  const labelX = ox + border;
  const labelY = oy + border;
  const labelW = lw - 2 * border;
  const labelH = lh - 2 * border;

  // White background
  drawRoundRect(page, labelX, labelY, labelW, labelH, 6, { fill: true, fillColor: WHITE });

  // Outer border
  drawRoundRect(page, labelX, labelY, labelW, labelH, 6, { stroke: true, strokeColor: HC_DGREY, lineWidth: 0.8 });

  // Red top accent bar
  const accentH = 1.5 * mm;
  page.drawRectangle({ x: labelX, y: labelY + labelH - accentH, width: labelW, height: accentH, color: HC_RED });

  // Logo
  const logoH = 10 * mm;
  const logoW = 10 * mm;
  const logoX = labelX + pad;
  const logoY = labelY + labelH - accentH - logoH - 2 * mm;
  if (logoImageEmbed) {
    page.drawImage(logoImageEmbed, { x: logoX, y: logoY, width: logoW, height: logoH });
  }

  // Order ID top right
  const orderIdSize = 7.5;
  const orderIdW = boldFont.widthOfTextAtSize(order.order_id, orderIdSize);
  page.drawText(order.order_id, {
    x: labelX + labelW - pad - orderIdW,
    y: logoY + 3 * mm,
    size: orderIdSize, font: boldFont, color: HC_DARK
  });

  // Divider below header
  let curY = logoY - 3 * mm;
  page.drawLine({ start: { x: labelX + pad, y: curY }, end: { x: labelX + labelW - pad, y: curY }, color: HC_DGREY, thickness: 0.5 });
  curY -= 4.5 * mm;

  // SHIP TO
  page.drawText('SHIP TO', { x: labelX + pad, y: curY, size: 6.5, font: boldFont, color: HC_RED });
  curY -= 4.5 * mm;

  // Recipient name
  page.drawText(order.ship_to, { x: labelX + pad, y: curY, size: 12, font: boldFont, color: HC_DARK });
  curY -= 5.5 * mm;

  // Address lines
  const addrWidth = labelW - 2 * pad;
  const addrLines = wrapText(order.address, regularFont, 8.5, addrWidth);
  for (const line of addrLines) {
    page.drawText(line, { x: labelX + pad, y: curY, size: 8.5, font: regularFont, color: HC_DARK });
    curY -= 4 * mm;
  }
  page.drawText(order.city_pin, { x: labelX + pad, y: curY, size: 8.5, font: regularFont, color: HC_DARK });
  curY -= 4 * mm;

  page.drawText(`Ph: ${order.phone}`, { x: labelX + pad, y: curY, size: 8, font: regularFont, color: HC_MID });
  curY -= 5.5 * mm;

  // Divider
  page.drawLine({ start: { x: labelX + pad, y: curY + 1.5 * mm }, end: { x: labelX + labelW - pad, y: curY + 1.5 * mm }, color: HC_DGREY, thickness: 0.5 });
  curY -= 4 * mm;

  // ITEM
  page.drawText('ITEM', { x: labelX + pad, y: curY, size: 6.5, font: boldFont, color: HC_RED });
  curY -= 4.5 * mm;

  const itemLines = wrapText(order.name, boldFont, 9, addrWidth);
  for (const line of itemLines) {
    page.drawText(line, { x: labelX + pad, y: curY, size: 9, font: boldFont, color: HC_DARK });
    curY -= 4.5 * mm;
  }

  curY -= 1 * mm;

  // Badges row: Size | FRAGILE | PREPAID
  const badgeH = 6 * mm;
  const sizeW = 16 * mm;
  const fragileW = 18 * mm;
  const prepaidW = 18 * mm;

  badge(page, labelX + pad, curY - mm, sizeW, badgeH, order.size, HC_RED, boldFont, 8);
  badge(page, labelX + pad + sizeW + 3 * mm, curY - mm, fragileW, badgeH, 'FRAGILE', HC_AMBER, boldFont, 7.5);
  badge(page, labelX + labelW - pad - prepaidW, curY - mm, prepaidW, badgeH, 'PREPAID', HC_GREEN, boldFont, 7.5);

  curY -= 9 * mm;

  // Carrier
  page.drawText(`Carrier: ${order.carrier || 'Tirupati'}`, { x: labelX + pad, y: curY, size: 7, font: regularFont, color: HC_MID });
  curY -= 5 * mm;

  // Tirupati barcode box
  const boxH = 18 * mm;
  const boxW = labelW - 2 * pad;
  const boxX = labelX + pad;
  const boxY = curY - boxH;

  // Dashed box — simulate with short lines
  const dashLen = 3, gapLen = 3;
  const dashColor = HC_DGREY;
  const drawDashedLine = (x1, y1, x2, y2) => {
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ux = dx / len, uy = dy / len;
    let pos = 0, drawing = true;
    while (pos < len) {
      const segLen = Math.min(drawing ? dashLen : gapLen, len - pos);
      if (drawing) {
        page.drawLine({
          start: { x: x1 + ux * pos, y: y1 + uy * pos },
          end: { x: x1 + ux * (pos + segLen), y: y1 + uy * (pos + segLen) },
          color: dashColor, thickness: 0.6
        });
      }
      pos += segLen;
      drawing = !drawing;
    }
  };
  drawDashedLine(boxX, boxY, boxX + boxW, boxY);
  drawDashedLine(boxX, boxY + boxH, boxX + boxW, boxY + boxH);
  drawDashedLine(boxX, boxY, boxX, boxY + boxH);
  drawDashedLine(boxX + boxW, boxY, boxX + boxW, boxY + boxH);

  // Text inside barcode box
  const t1 = 'AFFIX COURIER BARCODE HERE';
  const t2 = 'Tirupati / Shipmozo';
  const t1W = regularFont.widthOfTextAtSize(t1, 6);
  const t2W = regularFont.widthOfTextAtSize(t2, 5.5);
  page.drawText(t1, { x: boxX + (boxW - t1W) / 2, y: boxY + boxH / 2 + mm, size: 6, font: regularFont, color: HC_DGREY });
  page.drawText(t2, { x: boxX + (boxW - t2W) / 2, y: boxY + boxH / 2 - 3 * mm, size: 5.5, font: regularFont, color: HC_DGREY });

  // Footer
  const footerH = 13 * mm;
  const footerY = labelY;
  const footerX = labelX;
  const footerW = labelW;

  page.drawRectangle({ x: footerX, y: footerY, width: footerW, height: footerH, color: HC_LGREY });

  // Red left bar
  page.drawRectangle({ x: footerX, y: footerY, width: 1.5 * mm, height: footerH, color: HC_RED });

  let retY = footerY + footerH - 4 * mm;
  page.drawText('RETURN TO:', { x: footerX + 4 * mm, y: retY, size: 6, font: boldFont, color: HC_DARK });
  retY -= 3.2 * mm;

  const returnLines = [
    'HUSTLE CULTURE  |  hustleculture.co.in',
    '12A Mandeville Garden, Flat 3D, 3rd Floor, Ballygunge',
    'Kolkata - 700019, West Bengal  |  Ph: 6289021789',
  ];
  for (const line of returnLines) {
    page.drawText(line, { x: footerX + 4 * mm, y: retY, size: 6.2, font: regularFont, color: HC_MID });
    retY -= 3 * mm;
  }
}

export async function generateLabelsPDF(orders) {
  const pdfDoc = await PDFDocument.create();

  // Load fonts
  const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
  const regularFont = await pdfDoc.embedFont(StandardFonts.Helvetica);

  // Load logo
  let logoImageEmbed = null;
  try {
    const logoRes = await fetch('/logo.png');
    const logoBytes = await logoRes.arrayBuffer();
    logoImageEmbed = await pdfDoc.embedPng(logoBytes);
  } catch (e) {
    console.warn('Logo not loaded:', e);
  }

  const positions = [
    { ox: MARGIN, oy: MARGIN + LABEL_H },           // top-left
    { ox: MARGIN + LABEL_W, oy: MARGIN + LABEL_H }, // top-right
    { ox: MARGIN, oy: MARGIN },                     // bottom-left
    { ox: MARGIN + LABEL_W, oy: MARGIN },           // bottom-right
  ];

  let page = null;

  for (let i = 0; i < orders.length; i++) {
    const pos = i % 4;
    if (pos === 0) {
      page = pdfDoc.addPage([A4_W, A4_H]);
    }
    const { ox, oy } = positions[pos];
    await drawLabel(page, orders[i], ox, oy, logoImageEmbed, boldFont, regularFont);
  }

  return await pdfDoc.save();
}
