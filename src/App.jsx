import { useState } from 'react';
import { generateLabelsPDF } from './generatePDF.js';

const EMPTY_ORDER = {
  order_id: '', name: '', size: '', ship_to: '', address: '', city_pin: '', phone: '', carrier: 'Tirupati'
};

// ── Styles
const S = {
  app: {
    minHeight: '100vh',
    background: '#f4f4f2',
    fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif",
  },
  header: {
    background: '#c22126',
    padding: '0 24px',
    position: 'sticky',
    top: 0,
    zIndex: 100,
    boxShadow: '0 2px 12px rgba(194,33,38,0.25)',
  },
  headerInner: {
    maxWidth: 720,
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 56,
  },
  logoChip: {
    background: '#fcf8c8',
    borderRadius: 4,
    padding: '4px 9px',
    fontWeight: 900,
    fontSize: 13,
    letterSpacing: '0.04em',
    color: '#c22126',
  },
  headerRight: {
    color: 'rgba(255,255,255,0.55)',
    fontSize: 11,
    letterSpacing: '0.06em',
  },
  body: {
    maxWidth: 720,
    margin: '0 auto',
    padding: '28px 20px 100px',
  },
  hint: {
    color: '#777',
    fontSize: 13,
    marginBottom: 24,
    lineHeight: 1.5,
  },
  card: {
    background: '#fff',
    border: '1px solid #e8e8e8',
    borderLeft: '3px solid #c22126',
    borderRadius: 8,
    padding: '20px 20px 16px',
    marginBottom: 12,
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardLabel: {
    fontFamily: 'monospace',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.08em',
    color: '#aaa',
  },
  removeBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#ccc',
    fontSize: 20,
    lineHeight: 1,
    padding: '0 2px',
    transition: 'color 0.15s',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 10,
  },
  fieldLabel: {
    display: 'block',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.08em',
    color: '#999',
    marginBottom: 5,
  },
  input: {
    width: '100%',
    border: '1px solid #e2e2e2',
    borderRadius: 5,
    padding: '8px 10px',
    fontSize: 13,
    color: '#111',
    fontFamily: 'inherit',
    outline: 'none',
    transition: 'border-color 0.15s',
    background: '#fafafa',
  },
  tagRow: {
    display: 'flex',
    gap: 6,
    marginTop: 14,
  },
  addBtn: {
    width: '100%',
    padding: '13px',
    background: 'transparent',
    border: '1.5px dashed #d0d0d0',
    borderRadius: 8,
    cursor: 'pointer',
    color: '#bbb',
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: '0.07em',
    transition: 'all 0.15s',
    marginBottom: 20,
  },
  generateBtn: (disabled, success, loading) => ({
    width: '100%',
    padding: '16px',
    background: disabled ? '#d0d0d0' : success ? '#1a7a3a' : '#c22126',
    border: 'none',
    borderRadius: 8,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: '#fff',
    fontSize: 13,
    fontWeight: 700,
    letterSpacing: '0.1em',
    transition: 'background 0.25s',
    boxShadow: disabled ? 'none' : '0 4px 14px rgba(194,33,38,0.3)',
  }),
  error: {
    background: '#fff3f3',
    border: '1px solid #f5c0c0',
    borderRadius: 6,
    padding: '12px 16px',
    marginBottom: 16,
    color: '#c22126',
    fontSize: 13,
  },
  footer: {
    textAlign: 'center',
    color: '#ccc',
    fontSize: 11,
    marginTop: 40,
    letterSpacing: '0.04em',
  },
};

function Tag({ label, color }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
      padding: '3px 9px', borderRadius: 20,
      border: `1px solid ${color}`, color, background: '#fff'
    }}>{label}</span>
  );
}

function Field({ label, value, onChange, placeholder, span = 1 }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ gridColumn: span === 2 ? '1 / -1' : undefined }}>
      <label style={S.fieldLabel}>{label}</label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ ...S.input, borderColor: focused ? '#c22126' : '#e2e2e2' }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
    </div>
  );
}

function OrderCard({ order, index, total, onChange, onRemove }) {
  const update = (field, val) => onChange(index, { ...order, [field]: val });
  return (
    <div style={S.card}>
      <div style={S.cardHeader}>
        <span style={S.cardLabel}>ORDER {index + 1} {total > 1 ? `/ ${total}` : ''}</span>
        {total > 1 && (
          <button
            style={S.removeBtn}
            onClick={() => onRemove(index)}
            onMouseEnter={e => e.target.style.color = '#c22126'}
            onMouseLeave={e => e.target.style.color = '#ccc'}
          >×</button>
        )}
      </div>
      <div style={S.grid}>
        <Field label="ORDER ID" value={order.order_id} onChange={v => update('order_id', v)} placeholder="e.g. HSTLOFFLINE0093" />
        <Field label="SIZE" value={order.size} onChange={v => update('size', v)} placeholder="e.g. UK 9 / One Size" />
        <Field label="ITEM NAME" value={order.name} onChange={v => update('name', v)} placeholder="e.g. New Balance 9060 Olivine" span={2} />
        <Field label="RECIPIENT NAME" value={order.ship_to} onChange={v => update('ship_to', v)} placeholder="Full name" />
        <Field label="PHONE" value={order.phone} onChange={v => update('phone', v)} placeholder="+91 XXXXX XXXXX" />
        <Field label="ADDRESS LINE" value={order.address} onChange={v => update('address', v)} placeholder="Street, area, landmark" span={2} />
        <Field label="CITY – PIN" value={order.city_pin} onChange={v => update('city_pin', v)} placeholder="e.g. Mumbai, Maharashtra – 400001" span={2} />
      </div>
      <div style={S.tagRow}>
        <Tag label="Tirupati" color="#555" />
        <Tag label="PREPAID" color="#1a7a3a" />
        <Tag label="FRAGILE" color="#c47000" />
      </div>
    </div>
  );
}

export default function App() {
  const [orders, setOrders] = useState([{ ...EMPTY_ORDER }]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const addOrder = () => setOrders([...orders, { ...EMPTY_ORDER }]);
  const removeOrder = (i) => setOrders(orders.filter((_, idx) => idx !== i));
  const updateOrder = (i, updated) => {
    const next = [...orders];
    next[i] = updated;
    setOrders(next);
  };

  const isValid = orders.every(o => o.order_id && o.name && o.ship_to && o.address && o.city_pin && o.phone);

  const generate = async () => {
    setError('');
    setSuccess(false);
    setLoading(true);
    try {
      const pdfBytes = await generateLabelsPDF(orders);
      const blob = new Blob([pdfBytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().slice(0, 10);
      a.download = `HC_Labels_${date}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      setError('Failed to generate PDF. Please check all fields and try again.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.app}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.headerInner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={S.logoChip}>HUSTLE</span>
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, letterSpacing: '0.1em', fontWeight: 600 }}>
              LABEL GENERATOR
            </span>
          </div>
          <span style={S.headerRight}>Internal Ops Tool</span>
        </div>
      </div>

      {/* Body */}
      <div style={S.body}>
        <p style={S.hint}>
          Fill in order details below. Add as many orders as needed — the PDF will be print-ready with 4 labels per A4 page.
        </p>

        {orders.map((order, i) => (
          <OrderCard key={i} order={order} index={i} total={orders.length}
            onChange={updateOrder} onRemove={removeOrder} />
        ))}

        <button
          style={S.addBtn}
          onClick={addOrder}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#c22126'; e.currentTarget.style.color = '#c22126'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#d0d0d0'; e.currentTarget.style.color = '#bbb'; }}
        >
          + ADD ANOTHER ORDER
        </button>

        {error && <div style={S.error}>{error}</div>}

        <button
          style={S.generateBtn(!isValid || loading, success, loading)}
          onClick={generate}
          disabled={!isValid || loading}
        >
          {loading ? 'GENERATING...' : success
            ? '✓ PDF DOWNLOADED'
            : `GENERATE PDF  ·  ${orders.length} LABEL${orders.length !== 1 ? 'S' : ''}`}
        </button>

        {!isValid && (
          <p style={{ textAlign: 'center', color: '#bbb', fontSize: 11, marginTop: 8 }}>
            Fill all required fields to enable
          </p>
        )}

        <p style={S.footer}>hustleculture.co.in · {new Date().getFullYear()}</p>
      </div>
    </div>
  );
}
