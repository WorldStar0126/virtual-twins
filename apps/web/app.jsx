// Main app — shell + nav + tweaks panel
const { useState: uS, useEffect: uE } = React;
const { useOperatorData } = window.VTApi;

function Sidebar({ page, nav, approvalCount }) {
  const items = [
    {id:'cards', label:'Business Cards', ic:'cards', group:'Brand'},
    {id:'dashboard', label:'Dashboard', ic:'home', group:'Operator'},
    {id:'job-new', label:'New video', ic:'plus', group:'Operator'},
    {id:'history', label:'Job history', ic:'folder', group:'Operator'},
    {id:'assets', label:'Client assets', ic:'user', group:'Operator'},
    {id:'endcards', label:'End card pools', ic:'layers', group:'Operator'},
    {id:'cost', label:'Spend & cost', ic:'coin', group:'Operator'},
    {id:'clip-approve', label:'Clip approval', ic:'eye', group:'Gates', badge: approvalCount},
    {id:'assembly', label:'Final assembly', ic:'film', group:'Gates'},
  ];
  const groups = [...new Set(items.map(i=>i.group))];

  return <div style={{
    width: 232, background: VT.bg1, borderRight: `1px solid ${VT.line}`,
    display:'flex', flexDirection:'column', height:'100vh', flexShrink:0,
  }}>
    {/* Brand */}
    <div style={{padding:'20px 18px 16px', display:'flex', alignItems:'center', gap:10, borderBottom:`1px solid ${VT.line}`}}>
      <img src="assets/vt-mark.png" width={30} height={30}/>
      <div style={{minWidth:0}}>
        <div style={{fontFamily:VT.display, fontWeight:700, fontSize:12, color:'#fff', letterSpacing:1.6, whiteSpace:'nowrap'}}>VIRTUAL TWINS</div>
        <div style={{fontSize:9, color:VT.textMuted, letterSpacing:1.4, textTransform:'uppercase', marginTop:2, whiteSpace:'nowrap'}}>Operator Studio</div>
      </div>
    </div>

    {/* Nav */}
    <div style={{flex:1, overflowY:'auto', padding:'14px 10px'}}>
      {groups.map(g => <div key={g} style={{marginBottom:18}}>
        <div style={{padding:'0 10px 6px', fontSize:9.5, color:VT.textMuted, letterSpacing:1.3, textTransform:'uppercase', fontWeight:600}}>{g}</div>
        {items.filter(i=>i.group===g).map(i => {
          const active = page===i.id || (page==='clip-approve' && i.id==='clip-approve');
          return <div key={i.id} onClick={()=>nav(i.id)} style={{
            display:'flex', alignItems:'center', gap:10, padding:'7px 10px', borderRadius:7,
            cursor:'pointer', marginBottom:1,
            background: active ? 'rgba(155,92,246,0.1)' : 'transparent',
            color: active ? '#fff' : VT.textDim,
            border: `1px solid ${active ? 'rgba(155,92,246,0.25)' : 'transparent'}`,
            position:'relative',
          }}
          onMouseEnter={e=>{if(!active) e.currentTarget.style.background='rgba(255,255,255,0.03)';}}
          onMouseLeave={e=>{if(!active) e.currentTarget.style.background='transparent';}}>
            {active && <div style={{position:'absolute', left:-10, top:'50%', transform:'translateY(-50%)', width:3, height:16, borderRadius:2, background: VT.gradBrand}}/>}
            {React.createElement(IC[i.ic], {width:14, height:14})}
            <span style={{fontSize:12.5, fontWeight: active?600:500, flex:1}}>{i.label}</span>
            {i.badge>0 && <span style={{fontSize:10, background:'rgba(242,201,122,0.16)', color:'#F2C97A', padding:'1px 6px', borderRadius:99, fontWeight:600, fontFamily: VT.mono}}>{i.badge}</span>}
          </div>;
        })}
      </div>)}
    </div>

    {/* Footer */}
    <div style={{padding:12, borderTop:`1px solid ${VT.line}`}}>
      <div style={{display:'flex', alignItems:'center', gap:10, padding:8, borderRadius:8, background:VT.bg3}}>
        <div style={{width:30, height:30, borderRadius:8, background: VT.gradBrand, display:'flex', alignItems:'center', justifyContent:'center', fontFamily:VT.display, fontSize:11, fontWeight:700, color:'#1A1208'}}>AM</div>
        <div style={{flex:1, minWidth:0}}>
          <div style={{fontSize:12, fontWeight:600, color:VT.text}}>Adam Mercer</div>
          <div style={{fontSize:10, color: VT.textMuted}}>Founder</div>
        </div>
        <IC.chevd width={12} height={12} style={{color:VT.textMuted}}/>
      </div>
    </div>
  </div>;
}

function Topbar({ page, tweakOn }) {
  return <div style={{
    height:50, borderBottom:`1px solid ${VT.line}`,
    display:'flex', alignItems:'center', padding:'0 24px', gap:16,
    background: VT.bg1,
  }}>
    <div style={{display:'flex', alignItems:'center', gap:6, fontSize:12, color: VT.textDim}}>
      <span>Operator Studio</span>
      <IC.chev width={12} height={12} style={{color:VT.textMuted}}/>
      <span style={{color:VT.text, fontWeight:500, textTransform:'capitalize'}}>{page.replace('-',' ')}</span>
    </div>

    <div style={{marginLeft:'auto', display:'flex', alignItems:'center', gap:12}}>
      <div style={{display:'flex', alignItems:'center', gap:8, padding:'6px 12px', background: VT.bg3, border:`1px solid ${VT.line}`, borderRadius:7, minWidth:260}}>
        <IC.search width={13} height={13} style={{color: VT.textMuted}}/>
        <span style={{fontSize:12, color: VT.textMuted}}>Search clients, jobs, end cards…</span>
        <span style={{marginLeft:'auto', padding:'1px 6px', background:VT.bg4, fontSize:10, color:VT.textDim, borderRadius:4, fontFamily:VT.mono}}>⌘K</span>
      </div>
      <div style={{width:1, height:20, background:VT.line}}/>
      <Pill tone="success" small><IC.coin width={10} height={10}/> $148 / $250 budget</Pill>
    </div>
  </div>;
}

// Single-flat cards page (not wrapped in shell)
function CardsPage() {
  return <BusinessCardsCanvas/>;
}

// App
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "startPage": "dashboard",
  "accent": "purple",
  "density": "comfortable"
}/*EDITMODE-END*/;

function App() {
  const [page, setPage] = uS(() => localStorage.getItem('vt_page') || TWEAK_DEFAULTS.startPage);
  const [arg, setArg]   = uS(() => localStorage.getItem('vt_arg') || null);
  const [tweakOpen, setTweakOpen] = uS(false);
  const [tweaks, setTweaks] = uS(TWEAK_DEFAULTS);
  const isAssetHeavyPage = page === "assets" || page === "endcards";
  const operator = useOperatorData(isAssetHeavyPage ? 0 : 5000);

  uE(()=>{ localStorage.setItem('vt_page', page); if(arg) localStorage.setItem('vt_arg', arg); },[page,arg]);

  const nav = (p, a=null) => {
    if (p === 'clip-approve' && a) localStorage.setItem('vt_last_clip_job_id', a);
    setPage(p);
    setArg(a);
    window.scrollTo(0,0);
  };
  const lastClipJobId = localStorage.getItem('vt_last_clip_job_id');
  const clipApproveJobId = arg || lastClipJobId || operator.jobs[0]?.id || 'job_48217';

  // Tweaks host protocol
  uE(() => {
    const handler = (e) => {
      if (!e.data) return;
      if (e.data.type==='__activate_edit_mode') setTweakOpen(true);
      if (e.data.type==='__deactivate_edit_mode') setTweakOpen(false);
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({type:'__edit_mode_available'},'*');
    return ()=>window.removeEventListener('message', handler);
  }, []);

  const setTweak = (k,v) => {
    const next = {...tweaks, [k]:v};
    setTweaks(next);
    window.parent.postMessage({type:'__edit_mode_set_keys', edits:{[k]:v}},'*');
  };

  // Cards is its own canvas page
  if (page==='cards') return <div style={{position:'relative', width:'100vw', height:'100vh'}}>
    <CardsPage/>
    <FloatingNav page={page} nav={nav}/>
    {tweakOpen && <TweaksPanel tweaks={tweaks} setTweak={setTweak} close={()=>setTweakOpen(false)}/>}
  </div>;

  const screen = (() => {
    switch(page) {
      case 'dashboard':    return <Dashboard nav={nav} clients={operator.clients} jobs={operator.jobs} loading={operator.loading} error={operator.error} connected={operator.connected}/>;
      case 'job-new':      return <JobNew nav={nav} clients={operator.clients} creatingJob={operator.creatingJob} onCreateJob={operator.createJob}/>;
      case 'clip-approve': return <ClipApprove nav={nav} jobId={clipApproveJobId} jobs={operator.jobs} clients={operator.clients} onApproval={operator.approveJob} onRegenerate={operator.regenerateClip1} onStop={operator.stopJob} actingOnJob={operator.actingOnJob} fetchEvents={operator.fetchEvents} fetchJobClips={operator.fetchJobClips} />;
      case 'assembly':     return <Assembly nav={nav} jobId={arg || operator.jobs[0]?.id || null} jobs={operator.jobs} clients={operator.clients} onAssemble={operator.assembleJob} actingOnJob={operator.actingOnJob}/>;
      case 'assets':       return <AssetsVault nav={nav} clientSlug={arg||operator.clients[0]?.slug||'dan-balkun'} clients={operator.clients}/>;
      case 'endcards':     return <EndCardPool nav={nav} clientSlug={arg||operator.clients[0]?.slug||'dan-balkun'}/>;
      case 'history':      return <History nav={nav} jobs={operator.jobs} clients={operator.clients} loading={operator.loading}/>;
      case 'cost':         return <CostView nav={nav}/>;
      default:             return <Dashboard nav={nav} clients={operator.clients} jobs={operator.jobs} loading={operator.loading} error={operator.error} connected={operator.connected}/>;
    }
  })();

  return <div style={{display:'flex', width:'100vw', height:'100vh', background: VT.bg0}}>
    <Sidebar page={page} nav={nav} approvalCount={operator.jobs.filter(j=>j.status==='awaiting_approval').length}/>
    <div style={{flex:1, display:'flex', flexDirection:'column', minWidth:0}}>
      <Topbar page={page} tweakOn={tweakOpen}/>
      <div style={{flex:1, overflowY:'auto'}}>
        {screen}
      </div>
    </div>
    {tweakOpen && <TweaksPanel tweaks={tweaks} setTweak={setTweak} close={()=>setTweakOpen(false)}/>}
  </div>;
}

// Floating nav for the cards page (no sidebar there)
function FloatingNav({ page, nav }) {
  return <div style={{
    position:'fixed', top:20, left:20, zIndex:500,
    display:'flex', gap:6, padding:6,
    background:'rgba(255,255,255,0.9)', backdropFilter:'blur(20px)',
    border:'1px solid rgba(0,0,0,0.08)', borderRadius:10,
    boxShadow:'0 4px 20px rgba(0,0,0,0.08)',
  }}>
    {[
      {id:'cards', label:'Business cards'},
      {id:'dashboard', label:'Operator UI →'},
    ].map(t =>
      <button key={t.id} onClick={()=>nav(t.id)} style={{
        padding:'7px 12px', borderRadius:6, border:'none', cursor:'pointer',
        background: page===t.id ? '#1A1625' : 'transparent',
        color: page===t.id ? '#fff' : '#1A1625',
        fontSize:12, fontWeight:600, fontFamily: VT.body,
      }}>{t.label}</button>
    )}
  </div>;
}

function TweaksPanel({ tweaks, setTweak, close }) {
  return <div style={{
    position:'fixed', right:18, bottom:18, width:280, zIndex:600,
    background: VT.bg2, border: `1px solid ${VT.lineHi}`,
    borderRadius:12, padding:16, boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  }}>
    <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12}}>
      <div style={{fontFamily:VT.display, fontSize:13, fontWeight:700, color:VT.text, letterSpacing:1, textTransform:'uppercase'}}>Tweaks</div>
      <button onClick={close} style={{background:'none', border:'none', color:VT.textDim, cursor:'pointer', padding:0}}>
        <IC.x width={14} height={14}/>
      </button>
    </div>

    <div style={{marginBottom:14}}>
      <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Landing page</div>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:4}}>
        {['cards','dashboard','job-new','clip-approve'].map(o =>
          <button key={o} onClick={()=>{setTweak('startPage',o); localStorage.setItem('vt_page',o); location.reload();}} style={{
            padding:'6px 8px', fontSize:11, fontWeight:600, borderRadius:6,
            border:`1px solid ${tweaks.startPage===o ? 'rgba(155,92,246,0.4)' : VT.line}`,
            background: tweaks.startPage===o ? 'rgba(155,92,246,0.1)' : VT.bg3,
            color: tweaks.startPage===o ? '#C9A8FA' : VT.textDim,
            cursor:'pointer', textTransform:'capitalize',
          }}>{o.replace('-',' ')}</button>
        )}
      </div>
    </div>

    <div style={{marginBottom:14}}>
      <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Accent</div>
      <div style={{display:'flex', gap:6}}>
        {[
          {id:'purple', bg:'#9B5CF6'},
          {id:'gold',   bg:'#E8B860'},
          {id:'blend',  bg:'linear-gradient(135deg,#B57CF8,#E8B860)'},
        ].map(o =>
          <button key={o.id} onClick={()=>setTweak('accent',o.id)} style={{
            flex:1, padding:'8px 0', borderRadius:6,
            border:`1px solid ${tweaks.accent===o.id ? '#fff3' : VT.line}`,
            background: o.bg, cursor:'pointer',
            fontSize:10.5, fontWeight:700, color:'#0E0F13', textTransform:'uppercase', letterSpacing:.8,
            height:28,
          }}>{tweaks.accent===o.id?'✓':''}</button>
        )}
      </div>
    </div>

    <div style={{fontSize:11, color: VT.textDim, lineHeight:1.5, padding:10, background:VT.bg3, borderRadius:7, border:`1px solid ${VT.line}`}}>
      Tip: the sidebar is the primary nav. Try the <b style={{color:'#F2C97A'}}>approval gate</b> on the clip-approve screen — it's the core loop.
    </div>
  </div>;
}

window.App = App;
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
