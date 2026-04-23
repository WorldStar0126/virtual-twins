// Virtual Twins design tokens — shared across cards & UI
const VT = {
  // Backgrounds (dark scale)
  bg0: '#08090C',    // near black (deepest)
  bg1: '#0E0F13',    // brand dark (matches logo bg)
  bg2: '#15171D',    // panel
  bg3: '#1A1D26',    // raised panel
  bg4: '#232733',    // hover / input
  bg5: '#2E3241',    // border-ish filled

  // Lines
  line:   'rgba(255,255,255,0.07)',
  lineHi: 'rgba(255,255,255,0.12)',
  lineBrand: 'rgba(155,92,246,0.35)',

  // Text
  text:   '#E8E8EE',
  textDim:'#9094A6',
  textMuted: '#60657A',

  // Brand primaries
  purple:    '#9B5CF6',
  purpleLt:  '#B57CF8',
  purpleDk:  '#6B3FD4',
  gold:      '#E8B860',
  goldLt:    '#F2C97A',
  goldDk:    '#B8822E',

  // Semantic
  success: '#4FD68A',
  warn:    '#F2C97A',
  danger:  '#F06571',
  info:    '#7CA7FF',

  // Signature gradient
  gradBrand: 'linear-gradient(135deg, #B57CF8 0%, #9B5CF6 40%, #E8B860 100%)',
  gradBrandSoft: 'linear-gradient(135deg, rgba(155,92,246,0.18) 0%, rgba(232,184,96,0.14) 100%)',
  gradPurple: 'linear-gradient(180deg, #B57CF8 0%, #9B5CF6 50%, #6B3FD4 100%)',
  gradGold: 'linear-gradient(180deg, #F2C97A 0%, #E8B860 50%, #B8822E 100%)',
  gradRadial: 'radial-gradient(ellipse 80% 60% at 20% 0%, rgba(155,92,246,0.18), transparent 60%), radial-gradient(ellipse 70% 50% at 100% 100%, rgba(232,184,96,0.14), transparent 55%)',

  // Shadows
  glow: '0 0 60px rgba(155,92,246,0.20), 0 0 120px rgba(232,184,96,0.08)',
  lift: '0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.4)',

  // Type
  display: "'Space Grotesk', system-ui, sans-serif",
  body:    "'Inter', system-ui, sans-serif",
  mono:    "'JetBrains Mono', ui-monospace, monospace",

  // Spacing
  r: { xs:4, sm:6, md:10, lg:14, xl:20, xxl:28 },
};

window.VT = VT;
