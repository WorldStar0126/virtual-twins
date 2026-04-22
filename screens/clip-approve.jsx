// Clip 1 approval gate — this is the heart of the new workflow
const { useState: useStateA } = React;

function ClipApprove({ nav, jobId }) {
  const { useEffect: useEffectA } = React;
  const [events, setEvents] = useStateA([]);
  const [eventsErr, setEventsErr] = useStateA("");
  const mock = JOBS.find(j=>j.id===jobId) || JOBS[0];
  const live = (window.__VT_LIVE_JOBS && window.__VT_LIVE_JOBS[jobId]) || null;
  const job = live ? {
    id: live.id,
    client: mock.client,
    template: mock.template,
    format: `${live.format_seconds}s`,
    status: live.status,
    stage: live.stage,
    clipsTotal: live.clip_total,
    cost: 0,
    costProjected: live.clip_total * 3,
    prompt: mock.prompt,
    thumb: mock.thumb,
  } : mock;
  const client = CLIENTS.find(c=>c.slug===job.client);
  const [playing, setPlaying] = useStateA(false);
  const [progress, setProgress] = useStateA(42);
  const [note, setNote] = useStateA('');

  useEffectA(() => {
    let cancelled = false;
    const session = window.__VT_SESSION;
    if (!session || !VT_API || !jobId) return;
    VT_API.getJobEvents(session.access_token, jobId)
      .then(data => { if (!cancelled) setEvents(data || []); })
      .catch(e => { if (!cancelled) setEventsErr(e.message || "Failed to load events"); });
    return () => { cancelled = true; };
  }, [jobId]);

  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    {/* Header */}
    <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:18}}>
      <Btn variant="subtle" onClick={()=>nav('dashboard')} style={{paddingLeft:8}}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Back</Btn>
      <div style={{width:1, height:20, background:VT.line}}/>
      <Avatar client={client} size={34}/>
      <div>
        <div style={{fontSize:12, color: VT.textDim}}>{client.name} · {job.template}</div>
        <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: VT.text, letterSpacing:-0.2}}>Clip 1 approval <span style={{color:VT.textMuted, fontFamily: VT.mono, fontSize:14, marginLeft:8}}>{job.id}</span></div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
        <Pill tone="warn"><IC.warn width={11} height={11}/> Approval gated · clips 2{job.format==='30s'?'/3':''} blocked</Pill>
      </div>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'1fr 420px', gap:20}}>
      {/* Main — video player */}
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        {/* Big player */}
        <div style={{
          aspectRatio:'16/9', borderRadius:14, overflow:'hidden', position:'relative',
          background:`linear-gradient(160deg, ${job.thumb}35, #050608 70%)`,
          border:`1px solid ${VT.lineHi}`,
        }}>
          {/* fake video composition */}
          <div style={{position:'absolute', inset:0, background: `radial-gradient(ellipse at 50% 45%, ${job.thumb}25, transparent 60%), radial-gradient(ellipse at 50% 100%, rgba(0,0,0,0.7), transparent)`}}/>
          {/* "client standing" silhouette */}
          <div style={{
            position:'absolute', left:'50%', top:'50%', transform:'translate(-50%, -50%)',
            width:180, height:260,
            background: `linear-gradient(180deg, ${job.thumb}50, ${job.thumb}15 60%, transparent)`,
            borderRadius:'50% 50% 20% 20% / 40% 40% 10% 10%',
            filter:'blur(2px)',
            opacity:0.85,
          }}/>
          {/* grain overlay */}
          <div style={{position:'absolute', inset:0, background:'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.03), transparent 40%)'}}/>

          {/* overlay play btn */}
          {!playing && <div style={{position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center'}}>
            <button onClick={()=>setPlaying(true)} style={{
              width:72, height:72, borderRadius:36,
              background:'rgba(255,255,255,0.1)', border:'1px solid rgba(255,255,255,0.25)',
              backdropFilter:'blur(12px)', cursor:'pointer',
              display:'flex', alignItems:'center', justifyContent:'center',
            }}>
              <IC.play width={28} height={28} style={{color:'#fff', marginLeft:3}}/>
            </button>
          </div>}

          {/* meta bar */}
          <div style={{position:'absolute', top:14, left:14, right:14, display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
            <div style={{display:'flex', gap:8}}>
              <Pill tone="brand" small>CLIP 1 / {job.clipsTotal}</Pill>
              <Pill tone="neutral" small>10.0s · 720p · 9:16</Pill>
            </div>
            <div style={{fontFamily: VT.mono, fontSize:11, color:'rgba(255,255,255,0.6)'}}>seed: 48217_01</div>
          </div>

          {/* Scrubber */}
          <div style={{position:'absolute', bottom:0, left:0, right:0, padding:'12px 16px', background:'linear-gradient(180deg, transparent, rgba(0,0,0,0.8))'}}>
            <div style={{display:'flex', alignItems:'center', gap:12}}>
              <button onClick={()=>setPlaying(!playing)} style={{background:'none', border:'none', cursor:'pointer', color:'#fff'}}>
                {playing ? <IC.pause width={18} height={18}/> : <IC.play width={18} height={18}/>}
              </button>
              <span style={{fontFamily:VT.mono, fontSize:11, color:'rgba(255,255,255,0.85)'}}>0:0{Math.floor(progress/10)}</span>
              <div style={{flex:1, height:4, background:'rgba(255,255,255,0.15)', borderRadius:2, position:'relative', cursor:'pointer'}}
                   onClick={e=>{ const r = e.currentTarget.getBoundingClientRect(); setProgress(((e.clientX-r.left)/r.width)*100); }}>
                <div style={{position:'absolute', left:0, top:0, height:'100%', width:`${progress}%`, background: VT.gradBrand, borderRadius:2}}/>
                <div style={{position:'absolute', left:`${progress}%`, top:'50%', transform:'translate(-50%,-50%)', width:12, height:12, borderRadius:6, background:'#fff'}}/>
              </div>
              <span style={{fontFamily:VT.mono, fontSize:11, color:'rgba(255,255,255,0.5)'}}>0:10</span>
            </div>
          </div>
        </div>

        {/* Prompt recall */}
        <Panel pad={16}>
          <SectionHeader title="What we asked for" eyebrow="Prompt used"/>
          <div style={{padding:12, background: VT.bg4, borderRadius:8, fontSize:12.5, color: VT.textDim, lineHeight:1.6, fontFamily: VT.body}}>
            {job.prompt}
          </div>
          <div style={{display:'flex', gap:6, marginTop:10, flexWrap:'wrap'}}>
            {['@Image1','@Image2','@Image3','@Image4','@Audio1'].map(r =>
              <span key={r} style={{padding:'3px 8px', background:'rgba(155,92,246,0.1)', color:'#B57CF8', fontSize:11, fontFamily:VT.mono, borderRadius:5, border:'1px solid rgba(155,92,246,0.2)'}}>{r}</span>
            )}
          </div>
        </Panel>

        {/* Approval decision */}
        <Panel pad={18} style={{
          background:'linear-gradient(135deg, rgba(155,92,246,0.04), rgba(232,184,96,0.03))',
          border:`1px solid ${VT.lineBrand}`,
        }}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14}}>
            <div>
              <div style={{fontFamily: VT.display, fontSize:16, fontWeight:600, color: VT.text}}>Decision</div>
              <div style={{fontSize:12, color: VT.textDim, marginTop:2}}>Approve to trigger clip {job.clipsTotal>2?'2 & 3':'2'} (~${(job.clipsTotal-1)*3.0}). Reject to save the spend.</div>
            </div>
            <span style={{fontSize:11, color: VT.textMuted}}>SLA: 4 hrs avg</span>
          </div>

          <div style={{display:'flex', gap:10, marginBottom:14}}>
            <Btn variant="brand" icon="check" size="lg" onClick={()=>nav('assembly', jobId)} style={{flex:1, justifyContent:'center'}}>Approve · fire clip 2{job.format==='30s'?'/3':''}</Btn>
            <Btn variant="gold" icon="retry" size="lg" style={{flex:1, justifyContent:'center'}}>Regenerate clip 1</Btn>
            <Btn variant="danger" icon="x" size="lg" onClick={()=>nav('dashboard')}>Reject & stop</Btn>
          </div>

          <div>
            <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Notes for clip 2 (optional)</div>
            <textarea value={note} onChange={e=>setNote(e.target.value)} placeholder='e.g. "In clip 2, move outside to the porch" or "Keep the same grade, push warmth +5%"'
              style={{width:'100%', minHeight:70, padding:12, background: VT.bg4, border:`1px solid ${VT.line}`, borderRadius:8, color: VT.text, fontSize:12.5, fontFamily: VT.body, resize:'vertical', outline:'none'}}/>
          </div>
        </Panel>
      </div>

      {/* Right rail */}
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        <Panel pad={16}>
          <SectionHeader title="Continuity for clip 2" eyebrow="Shared style"/>
          <div style={{display:'flex', flexDirection:'column', gap:8}}>
            {[
              {l:'Wardrobe',    v:'Charcoal suit, white shirt',   tone:'success'},
              {l:'Setting',     v:'Staged living room, warm',     tone:'success'},
              {l:'Lighting',    v:'Golden hour, direction L',     tone:'success'},
              {l:'Frame ref',   v:'Best frame of clip 1 extracted', tone:'info'},
              {l:'Voice',       v:'@Audio1 (cloned)',              tone:'success'},
            ].map(r =>
              <div key={r.l} style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:'8px 10px', background: VT.bg4, borderRadius:7}}>
                <div>
                  <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.5, textTransform:'uppercase', fontWeight:600}}>{r.l}</div>
                  <div style={{fontSize:12, color: VT.text, marginTop:2}}>{r.v}</div>
                </div>
                <Pill tone={r.tone} small>{r.tone==='info'?'auto':'locked'}</Pill>
              </div>
            )}
          </div>
        </Panel>

        <Panel pad={16}>
          <SectionHeader title="Quality signals" eyebrow="Auto-check"/>
          {[
            {l:'Face match', v:94, tone:'success'},
            {l:'Voice match', v:88, tone:'success'},
            {l:'Lip sync', v:76, tone:'warn'},
            {l:'Artifacts / glitches', v:12, inv:true, tone:'success'},
          ].map(m =>
            <div key={m.l} style={{marginBottom:10}}>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:11.5, marginBottom:4}}>
                <span style={{color: VT.textDim}}>{m.l}</span>
                <span style={{color: VT.text, fontFamily:VT.mono, fontWeight:600}}>{m.v}{m.inv?'':''}%</span>
              </div>
              <div style={{height:3, background:VT.bg4, borderRadius:2, overflow:'hidden'}}>
                <div style={{height:'100%', width:`${m.v}%`, background: m.tone==='success'?'#4FD68A': m.tone==='warn'?'#F2C97A':'#F06571'}}/>
              </div>
            </div>
          )}
        </Panel>

        <Panel pad={16}>
          <SectionHeader title="Cost & time" eyebrow="Run tracking"/>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
            <div>
              <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:4}}>Spent</div>
              <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: VT.text}}>${job.cost.toFixed(2)}</div>
              <div style={{fontSize:10.5, color: VT.textMuted, marginTop:2}}>clip 1 · standard</div>
            </div>
            <div>
              <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:4}}>Projected</div>
              <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: '#E8B860'}}>${job.costProjected.toFixed(2)}</div>
              <div style={{fontSize:10.5, color: VT.textMuted, marginTop:2}}>if all approve</div>
            </div>
          </div>
          <div style={{height:1, background: VT.line, margin:'14px 0'}}/>
          <div style={{fontSize:11, color: VT.textDim, display:'flex', alignItems:'center', gap:6}}>
            <IC.clock width={12} height={12}/> Clip 1 rendered in 3m 14s · started 6h ago
          </div>
        </Panel>
        <Panel pad={16}>
          <SectionHeader title="Run events" eyebrow={`${events.length} loaded`}/>
          {eventsErr && <div style={{fontSize:11, color:"#F06571", marginBottom:8}}>{eventsErr}</div>}
          <div style={{display:'flex', flexDirection:'column', gap:6, maxHeight:240, overflowY:'auto'}}>
            {events.slice(-10).map(e =>
              <div key={e.id} style={{padding:'7px 9px', borderRadius:7, background:VT.bg4, border:`1px solid ${VT.line}`}}>
                <div style={{fontSize:11.5, color:VT.text}}>{e.event_type}</div>
                <div style={{fontSize:10, color:VT.textMuted, fontFamily:VT.mono}}>{e.created_at}</div>
              </div>
            )}
            {events.length===0 && <div style={{fontSize:11, color:VT.textMuted}}>No live events yet.</div>}
          </div>
        </Panel>
      </div>
    </div>
  </div>;
}

window.ClipApprove = ClipApprove;
