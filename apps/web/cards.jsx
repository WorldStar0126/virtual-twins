// Business cards — 5 variants, front + back, on a design canvas.
// Standard US business card is 3.5" × 2" — at 96dpi, 336 × 192. We'll render at 2x for crisp shadows.
const CARD_W = 560, CARD_H = 320; // 3.5:2 ratio, 160 dpi equivalent

const INFO = {
  name: 'ADAM MERCER',
  title: 'Founder & Creative Director',
  phone: '+1 (401) 555 — 0187',
  email: 'adam@virtualtwins.ai',
  web:   'virtualtwins.ai',
  addr:  'Providence, Rhode Island',
  ig:    '@virtualtwinsai',
  li:    '/in/virtualtwins',
};

// ── Card frame wrapper with subtle tilt & soft shadow ──
function CardFrame({ children, tilt=0, label }) {
  return <div style={{
    width: CARD_W, height: CARD_H,
    position:'relative',
    borderRadius: 14,
    overflow:'hidden',
    boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 30px 60px -20px rgba(0,0,0,0.55), 0 8px 24px rgba(0,0,0,0.4)',
    transform: `rotate(${tilt}deg)`,
    fontFamily: VT.body,
  }}>
    {children}
  </div>;
}

function CardPair({ front, back, label }) {
  return <div style={{display:'flex', flexDirection:'column', gap:28, alignItems:'flex-start'}}>
    <div style={{fontSize:11, fontWeight:600, letterSpacing:1.5, textTransform:'uppercase', color:'rgba(40,30,20,0.55)', fontFamily: VT.body}}>{label}</div>
    <div style={{display:'flex', gap:36, alignItems:'center'}}>
      <div>
        <div style={{fontSize:10, fontWeight:500, color:'rgba(40,30,20,0.45)', marginBottom:10, letterSpacing:.8, textTransform:'uppercase'}}>Front</div>
        {front}
      </div>
      <div>
        <div style={{fontSize:10, fontWeight:500, color:'rgba(40,30,20,0.45)', marginBottom:10, letterSpacing:.8, textTransform:'uppercase'}}>Back</div>
        {back}
      </div>
    </div>
  </div>;
}

// ──────────────────────────────────────────────────────────────
// V1 — Signature Dark (matches website vibe most literally)
// ──────────────────────────────────────────────────────────────
function CardV1_Front() {
  return <CardFrame>
    <div style={{
      position:'absolute', inset:0, background: VT.bg1,
    }}/>
    {/* soft brand corner glows */}
    <div style={{position:'absolute', top:-80, left:-40, width:260, height:260, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(155,92,246,0.25), transparent 70%)', filter:'blur(4px)'}}/>
    <div style={{position:'absolute', bottom:-80, right:-40, width:280, height:280, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(232,184,96,0.2), transparent 70%)', filter:'blur(4px)'}}/>
    {/* hair-line border */}
    <div style={{position:'absolute', inset:8, border:'1px solid rgba(255,255,255,0.06)', borderRadius:10, pointerEvents:'none'}}/>

    <div style={{position:'absolute', inset:0, padding:'38px 40px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div style={{display:'flex', alignItems:'center', gap:14}}>
        <img src="assets/vt-mark.png" width={48} height={48} style={{display:'block'}}/>
        <div style={{minWidth:0}}>
          <div style={{fontFamily: VT.display, fontWeight:700, fontSize:15, color:'#fff', letterSpacing:3, whiteSpace:'nowrap'}}>VIRTUAL TWINS</div>
          <div style={{fontSize:9, color: VT.textMuted, letterSpacing:2.5, marginTop:3, textTransform:'uppercase', whiteSpace:'nowrap'}}>AI Video Production</div>
        </div>
      </div>

      <div>
        <div style={{fontFamily: VT.display, fontWeight:600, fontSize:24, color:'#fff', letterSpacing:2, marginBottom:4}}>{INFO.name}</div>
        <div style={{fontSize:12, color: VT.textDim, letterSpacing:.2}}>{INFO.title}</div>
      </div>
    </div>
  </CardFrame>;
}
function CardV1_Back() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background: VT.bg1}}/>
    <div style={{position:'absolute', top:-120, right:-80, width:320, height:320, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(155,92,246,0.2), transparent 70%)', filter:'blur(4px)'}}/>
    <div style={{position:'absolute', bottom:-120, left:-80, width:320, height:320, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(232,184,96,0.18), transparent 70%)', filter:'blur(4px)'}}/>
    <div style={{position:'absolute', inset:8, border:'1px solid rgba(255,255,255,0.06)', borderRadius:10}}/>

    <div style={{position:'absolute', inset:0, padding:'38px 40px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        {[
          {ic:'phone', txt: INFO.phone},
          {ic:'mail',  txt: INFO.email},
          {ic:'globe', txt: INFO.web},
          {ic:'pin',   txt: INFO.addr},
        ].map(row => <div key={row.txt} style={{display:'flex', alignItems:'center', gap:12, color:'#E8E8EE'}}>
          <div style={{width:28, height:28, borderRadius:6, background:'rgba(155,92,246,0.1)', border:'1px solid rgba(155,92,246,0.28)', display:'flex', alignItems:'center', justifyContent:'center', color:'#B57CF8'}}>
            {React.createElement(IC[row.ic], {width:14, height:14})}
          </div>
          <div style={{fontSize:12.5, fontFamily: VT.body, letterSpacing:.1}}>{row.txt}</div>
        </div>)}
      </div>

      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <div style={{display:'flex', gap:10, color: VT.textDim}}>
          <div style={{width:26, height:26, borderRadius:6, background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.08)', display:'flex', alignItems:'center', justifyContent:'center'}}>
            <IC.ig width={13} height={13}/>
          </div>
          <div style={{width:26, height:26, borderRadius:6, background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.08)', display:'flex', alignItems:'center', justifyContent:'center'}}>
            <IC.li width={13} height={13}/>
          </div>
        </div>
        <div className="vt-grad-text" style={{fontFamily: VT.display, fontSize:11, fontWeight:600, letterSpacing:2.5, textTransform:'uppercase'}}>Your Digital Twin</div>
      </div>
    </div>
  </CardFrame>;
}

// ──────────────────────────────────────────────────────────────
// V2 — Big Mark (full-bleed brand, logo huge on front, info on back)
// ──────────────────────────────────────────────────────────────
function CardV2_Front() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'#0B0C10'}}/>
    <div style={{position:'absolute', inset:0, background:'radial-gradient(ellipse at 30% 50%, rgba(155,92,246,0.28), transparent 60%), radial-gradient(ellipse at 75% 60%, rgba(232,184,96,0.22), transparent 60%)'}}/>
    {/* big mark centered-left */}
    <img src="assets/vt-mark.png" style={{position:'absolute', left:-20, top:'50%', transform:'translateY(-50%)', width:340, height:340, objectFit:'contain', opacity:1}}/>
    {/* wordmark & name anchored right */}
    <div style={{position:'absolute', right:36, top:'50%', transform:'translateY(-50%)', textAlign:'right'}}>
      <div style={{fontFamily: VT.display, fontWeight:700, fontSize:22, color:'#fff', letterSpacing:3}}>VIRTUAL</div>
      <div style={{fontFamily: VT.display, fontWeight:700, fontSize:22, color:'#fff', letterSpacing:3, marginTop:-2}}>TWINS</div>
      <div style={{width:40, height:1, background:'linear-gradient(90deg, transparent, rgba(232,184,96,0.8))', marginLeft:'auto', marginTop:14, marginBottom:12}}/>
      <div style={{fontSize:10, color:'rgba(232,184,96,0.85)', letterSpacing:3, textTransform:'uppercase', fontWeight:600}}>AI Video Studio</div>
    </div>
  </CardFrame>;
}
function CardV2_Back() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'#0B0C10'}}/>
    {/* vertical gold line element */}
    <div style={{position:'absolute', left:40, top:32, bottom:32, width:1, background:'linear-gradient(180deg, transparent, rgba(232,184,96,0.5) 20%, rgba(155,92,246,0.5) 80%, transparent)'}}/>

    <div style={{position:'absolute', inset:0, padding:'38px 40px 38px 70px', display:'flex', flexDirection:'column', justifyContent:'center'}}>
      <div style={{fontFamily: VT.display, fontWeight:700, fontSize:28, color:'#fff', letterSpacing:1.5, marginBottom:2}}>{INFO.name}</div>
      <div style={{fontSize:12, color:'rgba(232,184,96,0.85)', fontWeight:500, letterSpacing:1.8, textTransform:'uppercase', marginBottom:24}}>{INFO.title}</div>

      <div style={{display:'grid', gridTemplateColumns:'auto 1fr', columnGap:14, rowGap:8, fontSize:12}}>
        <div style={{color: VT.textMuted, fontSize:10, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, paddingTop:2}}>Call</div>
        <div style={{color:'#E8E8EE'}}>{INFO.phone}</div>
        <div style={{color: VT.textMuted, fontSize:10, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, paddingTop:2}}>Mail</div>
        <div style={{color:'#E8E8EE'}}>{INFO.email}</div>
        <div style={{color: VT.textMuted, fontSize:10, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, paddingTop:2}}>Web</div>
        <div className="vt-grad-text" style={{fontWeight:600}}>{INFO.web}</div>
      </div>
    </div>
  </CardFrame>;
}

// ──────────────────────────────────────────────────────────────
// V3 — Foil Line (minimal, matte black, logo as thin gold foil line sweep)
// ──────────────────────────────────────────────────────────────
function CardV3_Front() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'#09090B'}}/>
    {/* subtle noise texture feel via layered radials */}
    <div style={{position:'absolute', inset:0, opacity:0.4, background:'radial-gradient(ellipse at 20% 0%, rgba(255,255,255,0.04), transparent 60%)'}}/>
    <div style={{position:'absolute', inset:0, padding:'44px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div>
        {/* tiny mark */}
        <img src="assets/vt-mark.png" width={30} height={30} style={{display:'block', marginBottom: 18}}/>
        <div style={{fontFamily: VT.display, fontWeight:700, fontSize:38, color:'#F4F4F8', letterSpacing:-1, lineHeight:1}}>
          Virtual
        </div>
        <div className="vt-gold-text" style={{fontFamily: VT.display, fontWeight:700, fontSize:38, letterSpacing:-1, lineHeight:1, fontStyle:'italic'}}>
          Twins.
        </div>
      </div>
      <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between'}}>
        <div style={{fontSize:11, color: VT.textMuted, letterSpacing:2.5, textTransform:'uppercase'}}>Est. Providence ’26</div>
        {/* thin gold underline */}
        <div style={{width:46, height:2, background: VT.gradGold, borderRadius:2, boxShadow:'0 0 12px rgba(232,184,96,0.4)'}}/>
      </div>
    </div>
  </CardFrame>;
}
function CardV3_Back() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'#09090B'}}/>
    <div style={{position:'absolute', inset:0, padding:'44px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div>
        <div style={{fontSize:10, color: VT.textMuted, letterSpacing:2.5, textTransform:'uppercase', marginBottom:6}}>Founder</div>
        <div style={{fontFamily: VT.display, fontWeight:600, fontSize:22, color:'#F4F4F8', letterSpacing:-.3}}>{INFO.name.replace(/([A-Z])([A-Z]+)/g, (_,a,b)=>a+b.toLowerCase())}</div>
      </div>

      <div style={{display:'flex', flexDirection:'column', gap:6, fontSize:12, color:'#D0D1D9'}}>
        <div>{INFO.phone}</div>
        <div>{INFO.email}</div>
        <div className="vt-gold-text" style={{fontWeight:600}}>{INFO.web}</div>
      </div>
    </div>
    {/* sweep foil line */}
    <div style={{position:'absolute', top:'50%', right:0, width:120, height:1.5, background: VT.gradGold, boxShadow:'0 0 10px rgba(232,184,96,0.5)'}}/>
  </CardFrame>;
}

// ──────────────────────────────────────────────────────────────
// V4 — Dual Twin (split vertical: purple half + gold half, arrows frame)
// ──────────────────────────────────────────────────────────────
function CardV4_Front() {
  return <CardFrame>
    {/* two halves */}
    <div style={{position:'absolute', left:0, top:0, bottom:0, width:'50%', background:'linear-gradient(135deg, #2A1950 0%, #0E0F13 100%)'}}/>
    <div style={{position:'absolute', right:0, top:0, bottom:0, width:'50%', background:'linear-gradient(225deg, #4A3415 0%, #0E0F13 100%)'}}/>
    {/* seam mark */}
    <div style={{position:'absolute', left:'50%', top:0, bottom:0, width:1, background:'linear-gradient(180deg, rgba(232,184,96,0.6), rgba(155,92,246,0.6))', transform:'translateX(-50%)', opacity:.35}}/>
    {/* big mark at seam */}
    <img src="assets/vt-mark.png" style={{position:'absolute', left:'50%', top:'50%', transform:'translate(-50%,-50%)', width:200, height:200, objectFit:'contain', filter:'drop-shadow(0 6px 24px rgba(0,0,0,0.4))'}}/>

    {/* "virtual" on purple half, "twins" on gold half */}
    <div style={{position:'absolute', left:32, top:30, fontFamily: VT.display, fontWeight:700, fontSize:11, letterSpacing:3, color:'rgba(181,124,248,0.9)'}}>VIRTUAL</div>
    <div style={{position:'absolute', right:32, bottom:30, fontFamily: VT.display, fontWeight:700, fontSize:11, letterSpacing:3, color:'rgba(242,201,122,0.9)'}}>TWINS</div>
    <div style={{position:'absolute', right:32, top:30, fontSize:10, letterSpacing:2, color: VT.textMuted, textTransform:'uppercase'}}>Card №01</div>
    <div style={{position:'absolute', left:32, bottom:30, fontSize:10, letterSpacing:2, color: VT.textMuted, textTransform:'uppercase'}}>AI Video</div>
  </CardFrame>;
}
function CardV4_Back() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'#0E0F13'}}/>
    <div style={{position:'absolute', inset:0, background: VT.gradRadial}}/>

    <div style={{position:'absolute', inset:0, padding:'36px 40px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
        <div>
          <div style={{fontFamily: VT.display, fontWeight:700, fontSize:22, color:'#fff', letterSpacing:1}}>{INFO.name}</div>
          <div style={{fontSize:11, color: VT.textDim, marginTop:4, letterSpacing:1, textTransform:'uppercase'}}>{INFO.title}</div>
        </div>
        <img src="assets/vt-mark.png" width={40} height={40} style={{opacity:.9}}/>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'8px 20px', fontSize:11.5, color:'#E8E8EE'}}>
        <div style={{display:'flex', alignItems:'center', gap:8}}><IC.phone width={13} height={13} style={{color:'#B57CF8', flexShrink:0}}/> {INFO.phone}</div>
        <div style={{display:'flex', alignItems:'center', gap:8}}><IC.globe width={13} height={13} style={{color:'#E8B860', flexShrink:0}}/> {INFO.web}</div>
        <div style={{display:'flex', alignItems:'center', gap:8}}><IC.mail width={13} height={13} style={{color:'#B57CF8', flexShrink:0}}/> {INFO.email}</div>
        <div style={{display:'flex', alignItems:'center', gap:8}}><IC.pin width={13} height={13} style={{color:'#E8B860', flexShrink:0}}/> {INFO.addr}</div>
      </div>
    </div>
  </CardFrame>;
}

// ──────────────────────────────────────────────────────────────
// V5 — Cream Flip (light card, contrast to the dark deck)
// ──────────────────────────────────────────────────────────────
function CardV5_Front() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'linear-gradient(135deg, #F5F1E8 0%, #E8DCC4 100%)'}}/>
    {/* subtle purple-gold shadow gradient accent in corner */}
    <div style={{position:'absolute', bottom:-60, right:-60, width:260, height:260, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(155,92,246,0.18), transparent 70%)'}}/>
    <div style={{position:'absolute', top:-60, left:-60, width:220, height:220, borderRadius:'50%',
      background:'radial-gradient(circle, rgba(184,130,46,0.2), transparent 70%)'}}/>

    <div style={{position:'absolute', inset:0, padding:'40px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div>
        <img src="assets/vt-mark.png" width={44} height={44} style={{display:'block', filter:'drop-shadow(0 2px 8px rgba(0,0,0,0.1))'}}/>
      </div>
      <div>
        <div style={{fontFamily: VT.display, fontWeight:700, fontSize:28, color:'#1A1625', letterSpacing:-0.3, lineHeight:1}}>Virtual Twins<span style={{color:'#9B5CF6'}}>.</span></div>
        <div style={{fontSize:12, color:'#58506A', marginTop:8, letterSpacing:.2, maxWidth:320, lineHeight:1.4}}>
          AI-powered video content for real estate professionals. Your likeness. Your voice. Your market.
        </div>
      </div>
    </div>
  </CardFrame>;
}
function CardV5_Back() {
  return <CardFrame>
    <div style={{position:'absolute', inset:0, background:'linear-gradient(135deg, #F5F1E8 0%, #E8DCC4 100%)'}}/>

    <div style={{position:'absolute', inset:0, padding:'40px', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div>
        <div style={{fontFamily: VT.display, fontWeight:700, fontSize:20, color:'#1A1625', letterSpacing:-.2}}>{INFO.name}</div>
        <div style={{fontSize:11, color:'#6B3FD4', fontWeight:600, marginTop:3, letterSpacing:1, textTransform:'uppercase'}}>{INFO.title}</div>
      </div>

      <div style={{display:'flex', flexDirection:'column', gap:6, fontSize:12, color:'#2C2438', fontFamily: VT.body}}>
        <div style={{display:'flex', alignItems:'center', gap:10}}><div style={{width:3, height:3, background:'#9B5CF6', borderRadius:99}}/>{INFO.phone}</div>
        <div style={{display:'flex', alignItems:'center', gap:10}}><div style={{width:3, height:3, background:'#9B5CF6', borderRadius:99}}/>{INFO.email}</div>
        <div style={{display:'flex', alignItems:'center', gap:10}}><div style={{width:3, height:3, background:'#B8822E', borderRadius:99}}/><span style={{fontWeight:600, background:'linear-gradient(90deg,#6B3FD4,#B8822E)', WebkitBackgroundClip:'text', backgroundClip:'text', WebkitTextFillColor:'transparent'}}>{INFO.web}</span></div>
        <div style={{display:'flex', alignItems:'center', gap:10, color:'#58506A'}}><div style={{width:3, height:3, background:'#B8822E', borderRadius:99}}/>{INFO.addr}</div>
      </div>
    </div>
  </CardFrame>;
}

// ─────────────────────────────────────────────────────────────
// Business cards canvas
// ─────────────────────────────────────────────────────────────
function BusinessCardsCanvas() {
  return <DesignCanvas>
    <div style={{padding:'0 80px 120px'}}>
      {/* Title */}
      <div style={{marginBottom: 60, padding: '0 20px', maxWidth: 780}}>
        <div style={{fontSize:12, fontWeight:600, color:'rgba(40,30,20,0.5)', letterSpacing:2, textTransform:'uppercase', marginBottom:10}}>
          Brand · Stationery
        </div>
        <div style={{fontFamily: VT.display, fontSize:44, fontWeight:600, color:'rgba(20,15,10,0.9)', letterSpacing:-1, lineHeight:1.1, marginBottom:12}}>
          Virtual Twins — Business Cards
        </div>
        <div style={{fontSize:15, color:'rgba(40,30,20,0.65)', lineHeight:1.55, maxWidth:620}}>
          Five directions, all leaning into the dark premium palette from the logo and website. Standard US size (3.5″ × 2″). Each shows front + back together so you can judge the pair. My pick for v1: <b>Signature Dark</b> (closest to site), with <b>Big Mark</b> as a bolder backup.
        </div>
      </div>

      <div style={{display:'flex', flexDirection:'column', gap: 80, padding:'0 20px'}}>
        <CardPair label="01 — Signature Dark (hero pick, closest to virtualtwins.ai)"
          front={<CardV1_Front/>} back={<CardV1_Back/>}/>
        <CardPair label="02 — Big Mark (logo-forward, bold)"
          front={<CardV2_Front/>} back={<CardV2_Back/>}/>
        <CardPair label="03 — Foil Line (minimal, matte black with thin gold foil accents)"
          front={<CardV3_Front/>} back={<CardV3_Back/>}/>
        <CardPair label="04 — Dual Twin (literal twin split — purple half / gold half)"
          front={<CardV4_Front/>} back={<CardV4_Back/>}/>
        <CardPair label="05 — Cream Flip (inverted palette — warm cream, dark logo)"
          front={<CardV5_Front/>} back={<CardV5_Back/>}/>
      </div>

      <div style={{marginTop: 100, padding: '0 20px', maxWidth: 720, fontSize:13, color:'rgba(40,30,20,0.6)', lineHeight:1.6}}>
        <b style={{color:'rgba(20,15,10,0.85)'}}>Print notes.</b> All dark variants are printable as soft-touch laminate w/ spot-UV on the arrows (V1, V2, V4). V3 is designed for matte black stock with real gold foil stamping. V5 uses uncoated cream stock (Gmund Cotton Max White) — great with letterpress on the logo mark.
      </div>
    </div>
  </DesignCanvas>;
}

window.BusinessCardsCanvas = BusinessCardsCanvas;
