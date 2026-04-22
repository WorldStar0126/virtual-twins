// Final assembly + end card picker
const { useState: useStateAss } = React;

function Assembly({ nav, jobId }) {
  const job = JOBS.find(j=>j.id===jobId) || JOBS[0];
  const client = CLIENTS.find(c=>c.slug===job.client);
  const cards = END_CARDS[client.slug] || [];
  const [selCard, setSelCard] = useStateAss(cards[0]?.id);
  const [xfade, setXfade] = useStateAss(400);
  const [music, setMusic] = useStateAss('marble-morning');

  const duration = job.format==='20s' ? 23 : 33;

  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:18}}>
      <Btn variant="subtle" onClick={()=>nav('dashboard')}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Back</Btn>
      <div style={{width:1, height:20, background:VT.line}}/>
      <Avatar client={client} size={34}/>
      <div>
        <div style={{fontSize:12, color: VT.textDim}}>{client.name} · {job.template}</div>
        <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: VT.text, letterSpacing:-0.2}}>Final assembly</div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:8}}>
        <Btn variant="ghost" icon="download">Preview</Btn>
        <Btn variant="primary" icon="check" onClick={()=>nav('dashboard')}>Assemble & deliver</Btn>
      </div>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'1fr 400px', gap:20}}>
      {/* Timeline + clip preview */}
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        <Panel pad={18}>
          <SectionHeader title="Timeline" eyebrow={`${duration}s · final deliverable`}/>

          {/* Video track */}
          <div style={{marginBottom:10}}>
            <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Video</div>
            <div style={{display:'flex', gap:3, height:72, borderRadius:8, overflow:'hidden'}}>
              <div style={{flex:'10', background:`linear-gradient(120deg, ${job.thumb}50, ${job.thumb}20)`, position:'relative', display:'flex', alignItems:'flex-end', padding:8, border:`1px solid ${job.thumb}40`}}>
                <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono}}>CLIP 1 · 10s</span>
                <IC.check width={12} height={12} style={{position:'absolute', top:8, right:8, color:'#4FD68A'}}/>
              </div>
              <div style={{width: xfade/50, background: 'linear-gradient(90deg, rgba(155,92,246,0.5), rgba(232,184,96,0.5))', height:'100%'}}/>
              <div style={{flex:'10', background:`linear-gradient(120deg, ${job.thumb}40, ${job.thumb}15)`, position:'relative', display:'flex', alignItems:'flex-end', padding:8, border:`1px solid ${job.thumb}30`}}>
                <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono}}>CLIP 2 · 10s</span>
                <IC.check width={12} height={12} style={{position:'absolute', top:8, right:8, color:'#4FD68A'}}/>
              </div>
              {job.format==='30s' && <>
                <div style={{width: xfade/50, background:'linear-gradient(90deg, rgba(232,184,96,0.5), rgba(155,92,246,0.5))'}}/>
                <div style={{flex:'10', background:`linear-gradient(120deg, ${job.thumb}35, ${job.thumb}10)`, position:'relative', display:'flex', alignItems:'flex-end', padding:8, border:`1px solid ${job.thumb}25`}}>
                  <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono}}>CLIP 3 · 10s</span>
                </div>
              </>}
              <div style={{flex:'3', background:'linear-gradient(135deg, #2A1950, #1A1010)', position:'relative', display:'flex', alignItems:'flex-end', padding:8, border:'1px solid rgba(232,184,96,0.3)'}}>
                <span style={{fontSize:11, color:'#E8B860', fontFamily:VT.mono}}>END · 3s</span>
              </div>
            </div>
          </div>

          {/* Audio track */}
          <div>
            <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Music bed</div>
            <div style={{height:36, borderRadius:8, background: VT.bg4, border:`1px solid ${VT.line}`, padding:'0 12px', display:'flex', alignItems:'center', gap:10}}>
              <div style={{flex:1, height:18, display:'flex', alignItems:'center', gap:2}}>
                {Array.from({length:80}, (_,i) => {
                  const h = 4 + Math.abs(Math.sin(i*0.7)*12) + Math.abs(Math.cos(i*0.23)*6);
                  return <div key={i} style={{flex:1, height:h, background:'linear-gradient(180deg, rgba(155,92,246,0.4), rgba(155,92,246,0.15))', borderRadius:1}}/>;
                })}
              </div>
              <span style={{fontSize:11, color: VT.textDim, fontFamily:VT.mono}}>−16 dB · fade 0.4/1.0s</span>
            </div>
          </div>

          {/* Seam controls */}
          <div style={{display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10, marginTop:14}}>
            <div>
              <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.8, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Seam</div>
              <div style={{display:'flex', gap:3, padding:2, background: VT.bg4, borderRadius:6}}>
                {['hard cut','crossfade','dip to black'].map((o,i) =>
                  <button key={o} style={{flex:1, padding:'5px 6px', fontSize:10.5, fontWeight:600, borderRadius:4, border:'none', cursor:'pointer', background: i===1 ? VT.bg5 : 'transparent', color: i===1 ? VT.text : VT.textDim}}>{o}</button>
                )}
              </div>
            </div>
            <div>
              <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.8, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Xfade</div>
              <input type="range" min={0} max={1000} value={xfade} onChange={e=>setXfade(+e.target.value)} style={{width:'100%', accentColor:'#9B5CF6'}}/>
              <div style={{fontSize:10.5, color:VT.textDim, fontFamily: VT.mono}}>{xfade}ms</div>
            </div>
            <div>
              <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.8, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Music</div>
              <select value={music} onChange={e=>setMusic(e.target.value)} style={{width:'100%', padding:'6px 8px', background: VT.bg4, border:`1px solid ${VT.line}`, borderRadius:6, color: VT.text, fontSize:11.5, outline:'none'}}>
                <option value="marble-morning">Marble Morning (bed)</option>
                <option>Quiet Resolve</option>
                <option>Harbor Light</option>
                <option>(none)</option>
              </select>
            </div>
          </div>
        </Panel>

        {/* Full preview */}
        <Panel pad={14}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12}}>
            <div style={{fontSize:13, fontWeight:600, color: VT.text}}>Full preview · 9:16</div>
            <span style={{fontSize:11, color: VT.textDim, fontFamily:VT.mono}}>{duration}.{Math.floor(Math.random()*10)}s · 10.8 MB</span>
          </div>
          <div style={{display:'flex', gap:10, alignItems:'center'}}>
            <VideoThumb accent={job.thumb} w={120} h={213} playing progress={28} label="play full"/>
            <div style={{flex:1, display:'flex', flexDirection:'column', gap:8}}>
              <VideoThumb accent={job.thumb} w={'100%'} h={60} label="CLIP 1 → CLIP 2 seam"/>
              <VideoThumb accent="#E8B860" w={'100%'} h={60} label={`END CARD · ${cards.find(c=>c.id===selCard)?.name || 'select'}`}/>
            </div>
          </div>
        </Panel>
      </div>

      {/* End card picker */}
      <Panel pad={16}>
        <SectionHeader title="End card" eyebrow={`Pool · ${cards.length} cards`}
          action={<Btn variant="subtle" icon="plus" size="sm" onClick={()=>nav('endcards', client.slug)}>Manage pool</Btn>}/>

        <div style={{display:'flex', flexDirection:'column', gap:8}}>
          {cards.map(c =>
            <div key={c.id} onClick={()=>setSelCard(c.id)} style={{
              display:'flex', gap:10, padding:10, borderRadius:10, cursor:'pointer',
              background: selCard===c.id ? 'rgba(232,184,96,0.06)' : VT.bg3,
              border:`1px solid ${selCard===c.id ? 'rgba(232,184,96,0.35)' : VT.line}`,
            }}>
              <div style={{
                width:56, height:86, borderRadius:6, flexShrink:0,
                background: c.bg, border:`1px solid ${c.accent}50`,
                display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:4,
                position:'relative', overflow:'hidden',
              }}>
                <div style={{width:20, height:20, borderRadius:4, background: c.accent, opacity:.85}}/>
                <div style={{width:30, height:2, background: c.accent, opacity:.5}}/>
                <div style={{width:24, height:1.5, background: c.accent, opacity:.35}}/>
              </div>
              <div style={{flex:1, minWidth:0}}>
                <div style={{fontSize:12.5, fontWeight:600, color: VT.text}}>{c.name}</div>
                <div style={{fontSize:11, color: VT.textMuted, marginTop:2, textTransform:'capitalize'}}>{c.layout.replace('_',' ')} · {c.motion}</div>
                <div style={{display:'flex', gap:6, marginTop:6}}>
                  <span style={{fontSize:10, color: VT.textDim, fontFamily:VT.mono}}>used {c.usage}×</span>
                  <span style={{fontSize:10, color: VT.textMuted}}>· last {c.lastUsed}</span>
                </div>
              </div>
              {selCard===c.id && <IC.check width={16} height={16} style={{color:'#E8B860', flexShrink:0}}/>}
            </div>
          )}
        </div>

        <div style={{height:1, background: VT.line, margin:'16px 0'}}/>

        <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Rotation policy</div>
        <div style={{display:'flex', gap:4, padding:3, background: VT.bg4, borderRadius:7}}>
          {[
            {id:'random',label:'Random', ic:'sparkle'},
            {id:'round',label:'Round-robin', ic:'retry'},
            {id:'campaign',label:'Campaign', ic:'layers'},
          ].map((o,i) =>
            <button key={o.id} style={{
              flex:1, padding:'7px 4px', fontSize:10.5, fontWeight:600, borderRadius:5,
              border:'none', cursor:'pointer',
              background: i===1 ? VT.bg5 : 'transparent',
              color: i===1 ? VT.text : VT.textDim,
              display:'flex', alignItems:'center', justifyContent:'center', gap:4,
            }}>
              {React.createElement(IC[o.ic], {width:11, height:11})} {o.label}
            </button>
          )}
        </div>
        <div style={{fontSize:11, color: VT.textDim, marginTop:10, lineHeight:1.5, padding:10, background:'rgba(232,184,96,0.05)', border:'1px solid rgba(232,184,96,0.2)', borderRadius:7}}>
          <b style={{color:'#E8B860'}}>Round-robin</b> — next card in pool picked automatically. Override above for this video.
        </div>
      </Panel>
    </div>
  </div>;
}

window.Assembly = Assembly;
