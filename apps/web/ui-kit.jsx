// Shared UI kit — icons, buttons, pills, panels, avatars
const { useState, useEffect, useRef, useMemo } = React;

// ── Icons (inline SVG, stroke-based, 20px default) ──
const IC = {
  home: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 11l9-7 9 7v9a1 1 0 01-1 1h-5v-6h-6v6H4a1 1 0 01-1-1z"/></svg>,
  plus: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M12 5v14M5 12h14"/></svg>,
  play: (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M7 5v14l12-7z"/></svg>,
  pause:(p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>,
  check:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 13l4 4 10-11"/></svg>,
  x:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M6 6l12 12M18 6L6 18"/></svg>,
  chev: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M9 6l6 6-6 6"/></svg>,
  chevd:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M6 9l6 6 6-6"/></svg>,
  user: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>,
  film: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 14h18M7 4v16M17 4v16"/></svg>,
  wand: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M15 4V2M15 16v-2M9 9H7M23 9h-2M20 2l-1.5 1.5M12 12l7-7M5 20l5-5M18 13l4 4-3 3-4-4z"/></svg>,
  chart:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 21V7m6 14V3m6 18v-9m6 9V10"/></svg>,
  coin: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9 10h4.5a1.5 1.5 0 010 3H9h5a1.5 1.5 0 010 3H9"/></svg>,
  clock:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>,
  folder:(p)=> <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>,
  cards:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 11h18"/></svg>,
  layers:(p)=> <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 18l9 5 9-5"/></svg>,
  search:(p)=> <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>,
  bolt: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M13 2L3 14h7l-1 8 10-12h-7z"/></svg>,
  sparkle:(p)=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3l2.5 6 6 2.5-6 2.5L12 20l-2.5-6-6-2.5 6-2.5zM19 3l1 2.5L22.5 6 20 7l-1 2.5L18 7l-2.5-1L18 5z"/></svg>,
  retry:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 12a9 9 0 1015 -6.7L21 8M21 3v5h-5"/></svg>,
  upload:(p)=> <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 17V5M6 11l6-6 6 6M4 19h16"/></svg>,
  download:(p)=><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 5v12M6 13l6 6 6-6M4 21h16"/></svg>,
  phone:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z"/></svg>,
  mail: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>,
  globe:(p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/></svg>,
  pin:  (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 21s7-7 7-12a7 7 0 10-14 0c0 5 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>,
  ig:   (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...p}><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.1" fill="currentColor"/></svg>,
  fb:   (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M13 22v-8h3l1-4h-4V7.5c0-1.2.4-2 2.1-2H17V2.2C16.5 2.1 15.5 2 14.4 2 11.8 2 10 3.6 10 6.9V10H7v4h3v8z"/></svg>,
  li:   (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M4 4h4v4H4zM4 10h4v10H4zM10 10h4v1.8c.7-1.1 2-2 4-2 3.5 0 4 2.3 4 5V20h-4v-4.8c0-1.3-.4-2.2-1.7-2.2-1.4 0-2.3 1-2.3 2.2V20h-4z"/></svg>,
  dots: (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/></svg>,
  warn: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/></svg>,
  eye:  (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>,
  drive:(p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M7.5 3l4.5 8h-9zM14 4l-3.5 6 4.5 8 3.5-6zM3 16.5L5.5 21h13l2.5-4.5z" opacity=".7"/></svg>,
};

// ── Status pill ──
function Pill({ tone='neutral', children, small }) {
  const map = {
    neutral: { bg:'rgba(255,255,255,0.06)', fg:'#B8BCCB', dot:'#B8BCCB' },
    brand:   { bg:'rgba(155,92,246,0.16)',  fg:'#C9A8FA', dot:'#B57CF8' },
    gold:    { bg:'rgba(232,184,96,0.12)',  fg:'#E8B860', dot:'#E8B860' },
    success: { bg:'rgba(79,214,138,0.12)',  fg:'#4FD68A', dot:'#4FD68A' },
    warn:    { bg:'rgba(242,201,122,0.14)', fg:'#F2C97A', dot:'#F2C97A' },
    danger:  { bg:'rgba(240,101,113,0.14)', fg:'#F06571', dot:'#F06571' },
    info:    { bg:'rgba(124,167,255,0.14)', fg:'#7CA7FF', dot:'#7CA7FF' },
  };
  const t = map[tone] || map.neutral;
  return <span style={{
    display:'inline-flex', alignItems:'center', gap:6,
    background: t.bg, color: t.fg,
    fontSize: small?10:11, fontWeight:600, letterSpacing: .2,
    padding: small ? '2px 7px' : '3px 9px',
    borderRadius: 999,
    fontFamily: VT.body,
  }}>
    <span style={{width:5, height:5, borderRadius:99, background:t.dot, boxShadow:`0 0 8px ${t.dot}`}}/>
    {children}
  </span>;
}

// ── Button ──
function Btn({ variant='ghost', size='md', icon, children, onClick, style, disabled }) {
  const base = {
    display:'inline-flex', alignItems:'center', gap:8,
    fontFamily: VT.body, fontWeight:600, fontSize: size==='sm'?12:13,
    padding: size==='sm'?'6px 10px': size==='lg'?'11px 18px':'8px 14px',
    borderRadius: 8, border:'1px solid transparent', cursor: disabled?'not-allowed':'pointer',
    letterSpacing: .1, transition:'all .15s ease', userSelect:'none',
    opacity: disabled?0.5:1,
  };
  const variants = {
    primary: { background: VT.gradBrand, color:'#0E0F13' },
    brand:   { background: 'linear-gradient(135deg,#9B5CF6,#6B3FD4)', color:'#fff', boxShadow:'0 1px 0 rgba(255,255,255,0.1) inset, 0 4px 16px rgba(155,92,246,0.3)' },
    gold:    { background: VT.gradGold, color:'#1A1208' },
    solid:   { background: VT.bg3, color: VT.text, border:`1px solid ${VT.lineHi}` },
    ghost:   { background:'transparent', color: VT.text, border:`1px solid ${VT.lineHi}` },
    danger:  { background:'rgba(240,101,113,0.1)', color:'#F06571', border:'1px solid rgba(240,101,113,0.3)' },
    subtle:  { background:'transparent', color: VT.textDim, border:'1px solid transparent' },
  };
  return <button onClick={disabled?undefined:onClick} style={{...base, ...variants[variant], ...style}}>
    {icon && React.createElement(IC[icon], {width: size==='sm'?14:16, height: size==='sm'?14:16})}
    {children}
  </button>;
}

// ── Panel / Card container ──
function Panel({ children, style, pad=16, elev=1 }) {
  const elevStyles = {
    0: { background: VT.bg2, border: `1px solid ${VT.line}` },
    1: { background: VT.bg3, border: `1px solid ${VT.line}` },
    2: { background: VT.bg3, border: `1px solid ${VT.lineHi}`, boxShadow: VT.lift },
  };
  return <div style={{ borderRadius: 12, padding: pad, ...elevStyles[elev], ...style }}>{children}</div>;
}

// ── Avatar ──
function Avatar({ client, size=32 }) {
  return <div style={{
    width:size, height:size, flexShrink:0,
    borderRadius: size<28?7:9,
    background: `linear-gradient(135deg, ${client.color}33, ${client.color}11)`,
    border:`1px solid ${client.color}55`,
    display:'flex', alignItems:'center', justifyContent:'center',
    fontFamily: VT.display, fontWeight: 700,
    fontSize: size * 0.38, color: client.color,
    letterSpacing: .3,
  }}>{client.initials}</div>;
}

// ── Logo mark (inline) ──
function VTMark({ size=24 }) {
  return <img src="assets/vt-mark.png" alt="" width={size} height={size}
    style={{display:'block', objectFit:'contain'}}/>;
}

// ── Section header for panels ──
function SectionHeader({ eyebrow, title, action }) {
  return <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between', marginBottom:14}}>
    <div>
      {eyebrow && <div style={{fontSize:10, fontWeight:600, color: VT.textMuted, letterSpacing:1.2, textTransform:'uppercase', marginBottom:4}}>{eyebrow}</div>}
      <div style={{fontFamily: VT.display, fontSize:18, fontWeight:600, color: VT.text, letterSpacing: -0.2}}>{title}</div>
    </div>
    {action}
  </div>;
}

// ── Thumbnail — fake video frame with gradient + play triangle ──
function VideoThumb({ accent='#9B5CF6', label, w=120, h=213, playing=false, progress=0 }) {
  return <div style={{
    width:w, height:h, flexShrink:0,
    borderRadius:10, position:'relative', overflow:'hidden',
    background: `linear-gradient(160deg, ${accent}40, ${accent}15 40%, #0a0b0f 100%)`,
    border:`1px solid ${accent}30`,
  }}>
    {/* body silhouette fake */}
    <div style={{position:'absolute', inset:0, background: `radial-gradient(circle at 50% 42%, rgba(255,255,255,0.05), transparent 42%), radial-gradient(circle at 50% 95%, ${accent}25, transparent 60%)`}}/>
    <div style={{position:'absolute', left:'50%', top:'40%', transform:'translate(-50%,-50%)', width:44, height:44, borderRadius:22, background:'rgba(255,255,255,0.1)', border:'1px solid rgba(255,255,255,0.2)', backdropFilter:'blur(8px)', display:'flex', alignItems:'center', justifyContent:'center'}}>
      {playing ? <IC.pause width={18} height={18} style={{color:'#fff'}}/> : <IC.play width={16} height={16} style={{color:'#fff', marginLeft:2}}/>}
    </div>
    {label && <div style={{position:'absolute', bottom:8, left:8, right:8, fontSize:10, fontWeight:500, color:'rgba(255,255,255,0.9)', fontFamily: VT.mono}}>{label}</div>}
    {progress>0 && <div style={{position:'absolute', bottom:0, left:0, height:2, width:`${progress}%`, background: accent}}/>}
  </div>;
}

Object.assign(window, { IC, Pill, Btn, Panel, Avatar, VTMark, SectionHeader, VideoThumb });
