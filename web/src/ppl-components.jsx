// ppl-components.jsx — Shared UI primitives for Passive Portfolio Lab
// All components exported to window for use by ppl-app.jsx

// ── Badge ────────────────────────────────────────────────────────────────────
const Badge = ({ label, variant = 'blue' }) => {
  const colors = {
    blue:  ['#d2e4f5','#0a326e'],
    green: ['#d4f0e0','#0e5a2a'],
    amber: ['#fef3c7','#7a4a00'],
    gray:  ['#f0f2f6','#555'],
    red:   ['#fff5f5','#c0392b'],
    navy:  ['#0a326e','#fff'],
  };
  const [bg, color] = colors[variant] || colors.gray;
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 9999,
      fontSize: 11, fontWeight: 700, letterSpacing: '0.04em',
      textTransform: 'uppercase', background: bg, color,
    }}>
      {label}
    </span>
  );
};

// ── MetricCard ───────────────────────────────────────────────────────────────
const MetricCard = ({ label, value, delta, deltaPositive, sub }) => (
  <div style={{
    background: '#fff', border: '1px solid #e8edf3', borderRadius: 10,
    padding: '16px 20px', minWidth: 0, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  }}>
    <div style={{
      fontSize: 11, color: '#6b727e', fontWeight: 700, textTransform: 'uppercase',
      letterSpacing: '0.06em', marginBottom: 6,
    }}>{label}</div>
    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#111', lineHeight: 1.15 }}>{value}</div>
    {delta && (
      <div style={{ fontSize: 12, color: deltaPositive ? '#21a350' : '#e53e3e', marginTop: 5, fontWeight: 600 }}>
        {delta}
      </div>
    )}
    {sub && <div style={{ fontSize: 12, color: '#999', marginTop: 3 }}>{sub}</div>}
  </div>
);

// ── SectionTitle ─────────────────────────────────────────────────────────────
const SectionTitle = ({ icon, title, caption }) => (
  <div style={{ marginBottom: 28 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
      {icon && <span style={{ fontSize: 22 }}>{icon}</span>}
      <h2 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: '#0d1f3c', lineHeight: 1.2 }}>{title}</h2>
    </div>
    {caption && (
      <p style={{ margin: 0, fontSize: 14, color: '#6b727e', paddingLeft: icon ? 32 : 0, lineHeight: 1.6 }}>
        {caption}
      </p>
    )}
    <div style={{
      height: 3, width: 48, background: '#4182b9', borderRadius: 9999,
      marginTop: 10, marginLeft: icon ? 32 : 0,
    }} />
  </div>
);

// ── InfoBanner ───────────────────────────────────────────────────────────────
const InfoBanner = ({ children, type = 'info' }) => {
  const styles = {
    info:    { bg: '#eff5fb', border: '#4182b9', color: '#1f3b5c' },
    success: { bg: '#f0faf4', border: '#21a350', color: '#0e5a2a' },
    warning: { bg: '#fff8f0', border: '#e8a000', color: '#7a4a00' },
    error:   { bg: '#fff5f5', border: '#e53e3e', color: '#7a0000' },
  };
  const s = styles[type] || styles.info;
  return (
    <div style={{
      background: s.bg, borderLeft: `3px solid ${s.border}`, color: s.color,
      borderRadius: 6, padding: '10px 16px', fontSize: 14,
      lineHeight: 1.65, marginBottom: 20,
    }}>
      {children}
    </div>
  );
};

// ── Btn ──────────────────────────────────────────────────────────────────────
const Btn = ({ children, onClick, variant = 'primary', disabled = false, small = false }) => {
  const variants = {
    primary:   { bg: '#4182b9', color: '#fff',   border: '#4182b9', hbg: '#1e5a96', hborder: '#1e5a96' },
    secondary: { bg: 'transparent', color: '#4182b9', border: '#4182b9', hbg: '#eff5fb', hborder: '#4182b9' },
    ghost:     { bg: '#f0f2f6', color: '#333',   border: '#e0e4eb', hbg: '#e0e4eb',  hborder: '#c8cdd6' },
    danger:    { bg: '#e53e3e', color: '#fff',   border: '#e53e3e', hbg: '#c0392b',  hborder: '#c0392b' },
  };
  const v = variants[variant] || variants.primary;
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        padding: small ? '5px 12px' : '8px 18px', borderRadius: 6,
        fontSize: small ? 13 : 14, fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: `1px solid ${disabled ? '#d0d7e2' : (hover ? v.hborder : v.border)}`,
        background: disabled ? '#f0f2f6' : (hover ? v.hbg : v.bg),
        color: disabled ? '#aaa' : v.color,
        transition: 'all 0.15s', fontFamily: 'inherit',
      }}
    >
      {children}
    </button>
  );
};

// ── ChartLine ─────────────────────────────────────────────────────────────────
// events:    [{ xMin, xMax, label, labelZh, color:'red'|'orange'|'purple' }]
// hLines:    [{ value, label, color }]
// extraInfo: parallel array to labels with drawdown values for tooltip
const ChartLine = ({ labels, datasets, height = 260, yFmt, events = [], extraInfo = [], hLines = [], lang = 'en' }) => {
  const ref = React.useRef();
  const chartRef = React.useRef();

  React.useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) chartRef.current.destroy();

    const EV_COLORS = {
      red:    { bg: 'rgba(229,62,62,0.09)',  border: 'rgba(229,62,62,0.30)',  text: '#c53030' },
      orange: { bg: 'rgba(214,105,0,0.09)',  border: 'rgba(214,105,0,0.30)',  text: '#a05000' },
      purple: { bg: 'rgba(107,57,196,0.09)', border: 'rgba(107,57,196,0.30)', text: '#6b39c4' },
    };

    const annotations = {};

    events.forEach((ev, i) => {
      const ec = EV_COLORS[ev.color] || EV_COLORS.red;
      const evLabel = lang === 'zh' ? (ev.labelZh || ev.label) : ev.label;
      annotations[`evBox${i}`] = {
        type: 'box', xMin: ev.xMin, xMax: ev.xMax,
        backgroundColor: ec.bg, borderColor: ec.border, borderWidth: 1,
      };
      annotations[`evLine${i}`] = {
        type: 'line', xMin: ev.xMin, xMax: ev.xMin,
        borderColor: ec.border, borderWidth: 1.5, borderDash: [3, 3],
        label: {
          display: true, content: evLabel, position: 'start', color: ec.text,
          backgroundColor: 'rgba(255,255,255,0.90)',
          font: { size: 10, weight: '600' },
          padding: { x: 5, y: 3 }, borderRadius: 4,
          yAdjust: 6, xAdjust: 4,
        },
      };
    });

    hLines.forEach((hl, i) => {
      annotations[`hLine${i}`] = {
        type: 'line', yMin: hl.value, yMax: hl.value,
        borderColor: hl.color || 'rgba(150,150,150,0.35)',
        borderWidth: 1, borderDash: [5, 4],
        label: {
          display: true, content: hl.label, position: '100%',
          color: hl.color || '#999', backgroundColor: 'transparent',
          font: { size: 10, weight: '600' }, xAdjust: -4,
        },
      };
    });

    chartRef.current = new Chart(ref.current, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 10, font: { size: 12 }, usePointStyle: true, pointStyleWidth: 10 },
          },
          tooltip: {
            backgroundColor: '#0d1f3c',
            titleColor: '#a8cae8',
            bodyColor: '#d2e4f5',
            borderColor: '#1e5a96',
            borderWidth: 1,
            padding: { x: 14, y: 12 },
            cornerRadius: 8,
            titleFont: { size: 12, weight: '700' },
            bodyFont: { size: 12 },
            callbacks: {
              title: items => '📅 ' + items[0].label,
              label: ctx => {
                const v = ctx.parsed.y;
                const fmt = yFmt ? yFmt(v, ctx.dataset.label) : v.toLocaleString();
                return `  ${ctx.dataset.label}: ${fmt}`;
              },
              afterBody: items => {
                const idx = items[0].dataIndex;
                if (extraInfo.length && extraInfo[idx] !== undefined) {
                  const dd = extraInfo[idx];
                  const bar = dd < -30 ? '🔴' : dd < -15 ? '🟡' : '🟢';
                  return ['', `  ${bar} Drawdown: ${dd.toFixed(1)}%`];
                }
                return [];
              },
            },
          },
          annotation: { annotations },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { maxTicksLimit: 10, font: { size: 11 }, color: '#888' },
          },
          y: {
            grid: { color: '#f0f2f6' },
            ticks: {
              font: { size: 11 }, color: '#888',
              callback: v => yFmt ? yFmt(v) : v.toLocaleString(),
            },
          },
        },
      },
    });

    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [
    JSON.stringify(labels),
    JSON.stringify(datasets),
    JSON.stringify(events),
    JSON.stringify(hLines),
    JSON.stringify(extraInfo),
    lang,
  ]);

  return <div style={{ height, position: 'relative' }}><canvas ref={ref} /></div>;
};

// ── ChartBar ─────────────────────────────────────────────────────────────────
const ChartBar = ({ labels, data, height = 220 }) => {
  const ref = React.useRef();
  const chartRef = React.useRef();

  React.useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(ref.current, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: data.map(v => v >= 0 ? '#4182b9' : '#e53e3e'),
          borderRadius: 3,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0d1f3c', titleColor: '#a8cae8', bodyColor: '#d2e4f5',
            borderColor: '#1e5a96', borderWidth: 1, cornerRadius: 8,
            callbacks: { label: ctx => `  Return: ${ctx.parsed.y.toFixed(1)}%` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
          y: {
            grid: { color: '#f0f2f6' },
            ticks: { font: { size: 11 }, color: '#888', callback: v => v + '%' },
          },
        },
      },
    });
    return () => { if (chartRef.current) chartRef.current.destroy(); };
  }, [JSON.stringify(labels), JSON.stringify(data)]);

  return <div style={{ height, position: 'relative' }}><canvas ref={ref} /></div>;
};

// ── Treemap ───────────────────────────────────────────────────────────────────
// items: [{ ticker, weight, name, cagr, vol, maxDD, sharpe, volTier }]
const Treemap = ({ items }) => {
  const [hovered, setHovered] = React.useState(null);
  if (!items || !items.length) return null;
  const sorted = [...items].sort((a, b) => b.weight - a.weight);

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, height: 280, borderRadius: 10, overflow: 'hidden' }}>
      {sorted.map(item => {
        const pct = (item.weight * 100).toFixed(1);
        const colorIdx = Math.min(Math.max(Math.floor(item.volTier ?? 2), 0), 5);
        const bg = PPL_BLUE6[colorIdx];
        const light = colorIdx <= 1;
        const tc  = light ? '#0a326e' : '#fff';
        const stc = light ? '#1e5a96' : 'rgba(255,255,255,0.75)';
        const isHov = hovered === item.ticker;

        return (
          <div
            key={item.ticker}
            onMouseEnter={() => setHovered(item.ticker)}
            onMouseLeave={() => setHovered(null)}
            style={{
              flexGrow: item.weight, flexBasis: `${item.weight * 100}%`,
              background: bg, display: 'flex', flexDirection: 'column',
              justifyContent: 'flex-end', padding: '8px 10px',
              cursor: 'default', filter: isHov ? 'brightness(1.12)' : 'none',
              transition: 'filter 0.15s', position: 'relative', minWidth: 40,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 700, color: tc, lineHeight: 1.2 }}>{item.ticker}</div>
            <div style={{ fontSize: 12, color: stc }}>{pct}%</div>
            {isHov && (
              <div style={{
                position: 'absolute', bottom: '100%', left: 0, zIndex: 20,
                background: '#0d1f3c', color: '#fff', borderRadius: 8,
                padding: '10px 14px', fontSize: 12, lineHeight: 1.6,
                whiteSpace: 'nowrap', boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
                border: '1px solid #1e5a96',
              }}>
                <div style={{ fontWeight: 700, marginBottom: 5, color: '#a8cae8' }}>
                  {item.ticker} — {item.name}
                </div>
                <div>Weight: <strong>{pct}%</strong> · CAGR: <strong>{item.cagr?.toFixed(1)}%</strong></div>
                <div>Vol: {item.vol?.toFixed(1)}% · Max DD: <span style={{ color: '#fc8181' }}>{item.maxDD?.toFixed(1)}%</span></div>
                <div>Sharpe: {item.sharpe?.toFixed(2)}</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ── Export to window ──────────────────────────────────────────────────────────
Object.assign(window, { Badge, MetricCard, SectionTitle, InfoBanner, Btn, ChartLine, ChartBar, Treemap });
