// Final assembly + end card picker
const { useState: useStateAss, useEffect: useEffectAss } = React;

function Assembly({ nav, jobId, jobs = [], clients = [], onAssemble, actingOnJob = false }) {
  const sourceJobs = jobs.length ? jobs : (window.JOBS || []);
  const sourceClients = clients.length ? clients : (window.CLIENTS || []);
  const job = sourceJobs.find((j)=>j.id===jobId) || sourceJobs[0] || null;
  const client = job ? (sourceClients.find((c)=>c.slug===job.client) || null) : null;
  const fallbackCards = client ? (END_CARDS[client.slug] || []) : [];
  const [cards, setCards] = useStateAss(fallbackCards);
  const [selCard, setSelCard] = useStateAss(null);
  const [xfade, setXfade] = useStateAss(400);
  const [music, setMusic] = useStateAss('marble-morning');
  const [seamType, setSeamType] = useStateAss("crossfade");
  const [rotationPolicy, setRotationPolicy] = useStateAss("round");
  const [clipSpeedByIdx, setClipSpeedByIdx] = useStateAss({});
  const [clipDurationByIdx, setClipDurationByIdx] = useStateAss({});
  const [clipUrlByIdx, setClipUrlByIdx] = useStateAss({});

  if (!job || !client) {
    return <div style={{padding:'24px 28px', color:VT.textDim}}>No matching job/client found. Open Final Assembly from a selected job.</div>;
  }

  const duration = job.format==='20s' ? 23 : 33;
  const api = window.VTApi?.Api;
  const apiBase = window.VTApi?.Api?.base || "";
  useEffectAss(() => {
    let active = true;
    if (!client?.slug || !api?.getClientAssets) {
      setCards(fallbackCards);
      return undefined;
    }
    const loadCards = async () => {
      try {
        const payload = await api.getClientAssets(client.slug);
        if (!active) return;
        const dynamicCards = (payload.end_cards || []).map((c, idx) => ({
          id: c.id,
          name: c.title || c.id,
          layout: "uploaded",
          motion: "video",
          usage: 0,
          lastUsed: "new",
          bg: "linear-gradient(135deg, #2A1950, #1A1010)",
          accent: "#E8B860",
          file: c.file,
          local_url: c.local_url,
        }));
        setCards(dynamicCards.length ? dynamicCards : fallbackCards);
      } catch (err) {
        if (!active) return;
        setCards(fallbackCards);
      }
    };
    loadCards();
    return () => {
      active = false;
    };
  }, [api, client?.slug]);
  useEffectAss(() => {
    let active = true;
    if (!job?.id || !api?.getJobClips) {
      setClipSpeedByIdx({});
      setClipDurationByIdx({});
      setClipUrlByIdx({});
      return undefined;
    }
    const loadClipMeta = async () => {
      try {
        const rows = await api.getJobClips(job.id);
        if (!active) return;
        const nextSpeed = {};
        const nextDuration = {};
        const nextUrl = {};
        (rows || []).forEach((row) => {
          const idx = Number(row?.clip);
          if (!idx) return;
          const speed = Number(row?.audio_speed || 0);
          if (speed > 0) nextSpeed[idx] = speed;
          const durationSec = Number(row?.duration_sec || 0);
          if (durationSec > 0) nextDuration[idx] = durationSec;
          const direct = row?.output_local_url ? `${apiBase}${row.output_local_url}` : toOutputUrl(row?.output_path);
          if (direct) nextUrl[idx] = direct;
        });
        setClipSpeedByIdx(nextSpeed);
        setClipDurationByIdx(nextDuration);
        setClipUrlByIdx(nextUrl);
      } catch (err) {
        if (!active) return;
        setClipSpeedByIdx({});
        setClipDurationByIdx({});
        setClipUrlByIdx({});
      }
    };
    loadClipMeta();
    return () => {
      active = false;
    };
  }, [api, apiBase, job?.id]);
  const toOutputUrl = (path) => {
    if (!path || !job?.client) return null;
    const normalized = String(path).replaceAll("\\", "/");
    const marker = `/output/${job.client}/`;
    const idx = normalized.indexOf(marker);
    if (idx < 0) return null;
    const rel = normalized.slice(idx + "/output".length);
    return `${apiBase}/output-files${rel}`;
  };
  const assembledVideoUrl = job?.final_output_local_url
    ? `${apiBase}${job.final_output_local_url}`
    : toOutputUrl(job?.final_output_path);
  const clipRows = Object.values(job?.clip_outputs || {}).sort((a, b) => Number(a?.clip || 0) - Number(b?.clip || 0));
  const clip1 = clipRows.find((row) => Number(row?.clip) === 1) || null;
  const clip2 = clipRows.find((row) => Number(row?.clip) === 2) || null;
  const clip3 = clipRows.find((row) => Number(row?.clip) === 3) || null;
  const cacheBuster = encodeURIComponent(String(job?.updated_at || job?.created_at || job?.id || ""));
  const clipStreamUrl = (idx) => (job?.id ? `${apiBase}/v1/jobs/${job.id}/clips/${idx}/stream?v=${cacheBuster}` : null);
  const clip1Url = clipStreamUrl(1) || clipUrlByIdx[1] || (clip1?.output_local_url ? `${apiBase}${clip1.output_local_url}` : toOutputUrl(clip1?.output_path));
  const clip2Url = clipStreamUrl(2) || clipUrlByIdx[2] || (clip2?.output_local_url ? `${apiBase}${clip2.output_local_url}` : toOutputUrl(clip2?.output_path));
  const clip3Url = clipStreamUrl(3) || clipUrlByIdx[3] || (clip3?.output_local_url ? `${apiBase}${clip3.output_local_url}` : toOutputUrl(clip3?.output_path));
  const fullPreviewUrl = assembledVideoUrl || null;
  const seamPreviewUrl = job?.seam_preview_local_url
    ? `${apiBase}${job.seam_preview_local_url}`
    : toOutputUrl(job?.seam_preview_path);
  const selectedCard = cards.find((c)=>c.id===selCard) || null;
  const selectedCardUrl = selectedCard?.local_url ? `${apiBase}${selectedCard.local_url}` : null;
  const previewAspect = String(job?.aspect_ratio || "9:16").replace(":", " / ");
  const fmtClipDuration = (idx) => {
    const sec = Number(clipDurationByIdx[idx] || 0);
    if (!sec) return "10s";
    const rounded = Math.max(1, Math.round(sec));
    return `${rounded}s`;
  };

  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:18}}>
      <Btn variant="subtle" onClick={()=>nav('dashboard')}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Back</Btn>
      <div style={{width:1, height:20, background:VT.line}}/>
      <Avatar client={client} size={34}/>
      <div>
        <div style={{fontSize:12, color: VT.textDim}}>
          {client.name}
          · {job.template}
          <span style={{margin:'0 8px', color:VT.textMuted, fontFamily:VT.mono}}>{job.id}</span>
        </div>
        <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: VT.text, letterSpacing:-0.2}}>Final assembly</div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:8}}>
        <Btn variant="ghost" icon="download">Preview</Btn>
        <Btn
          variant="primary"
          icon="check"
          disabled={actingOnJob}
          onClick={async ()=>{
            if (!onAssemble) return;
            await onAssemble(job.id, selCard || null, { seamType, xfadeMs: xfade });
          }}
        >
          {actingOnJob ? "Assembling..." : "Assemble & deliver"}
        </Btn>
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
              <div style={{
                flex:'10',
                background: `linear-gradient(120deg, ${job.thumb}50, ${job.thumb}20)`,
                position:'relative',
                display:'flex',
                alignItems:'flex-end',
                padding:8,
                border:`1px solid ${job.thumb}40`,
                overflow:'hidden'
              }}>
                {clip1Url && (
                  <video
                    src={clip1Url}
                    muted
                    preload="metadata"
                    onLoadedMetadata={(e)=>{
                      const dur = Number(e.currentTarget.duration || 0);
                      if (dur > 0.25) e.currentTarget.currentTime = Math.min(dur * 0.35, 2.0);
                    }}
                    style={{position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover'}}
                  />
                )}
                <div style={{position:'absolute', inset:0, background:'linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.35))'}}/>
                <div style={{position:'absolute', top:8, left:8, padding:'2px 6px', borderRadius:999, background:'rgba(10,12,20,0.65)', color:'#F2C97A', fontSize:10, fontFamily:VT.mono}}>
                  {clipSpeedByIdx[1] ? `${clipSpeedByIdx[1].toFixed(2)}x` : "n/a"}
                </div>
                <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono, position:'relative', zIndex:2}}>
                  CLIP 1 · {fmtClipDuration(1)}
                </span>
                <IC.check width={12} height={12} style={{position:'absolute', top:8, right:8, color:'#4FD68A'}}/>
              </div>
              <div style={{width: xfade/50, background: 'linear-gradient(90deg, rgba(155,92,246,0.5), rgba(232,184,96,0.5))', height:'100%'}}/>
              <div style={{
                flex:'10',
                background: `linear-gradient(120deg, ${job.thumb}40, ${job.thumb}15)`,
                position:'relative',
                display:'flex',
                alignItems:'flex-end',
                padding:8,
                border:`1px solid ${job.thumb}30`,
                overflow:'hidden'
              }}>
                {clip2Url && (
                  <video
                    src={clip2Url}
                    muted
                    preload="metadata"
                    onLoadedMetadata={(e)=>{
                      const dur = Number(e.currentTarget.duration || 0);
                      if (dur > 0.25) e.currentTarget.currentTime = Math.min(dur * 0.45, 2.5);
                    }}
                    style={{position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover'}}
                  />
                )}
                <div style={{position:'absolute', inset:0, background:'linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.35))'}}/>
                <div style={{position:'absolute', top:8, left:8, padding:'2px 6px', borderRadius:999, background:'rgba(10,12,20,0.65)', color:'#F2C97A', fontSize:10, fontFamily:VT.mono}}>
                  {clipSpeedByIdx[2] ? `${clipSpeedByIdx[2].toFixed(2)}x` : "n/a"}
                </div>
                <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono, position:'relative', zIndex:2}}>
                  CLIP 2 · {fmtClipDuration(2)}
                </span>
                <IC.check width={12} height={12} style={{position:'absolute', top:8, right:8, color:'#4FD68A'}}/>
              </div>
              {job.format==='30s' && <>
                <div style={{width: xfade/50, background:'linear-gradient(90deg, rgba(232,184,96,0.5), rgba(155,92,246,0.5))'}}/>
                <div style={{
                  flex:'10',
                  background: `linear-gradient(120deg, ${job.thumb}35, ${job.thumb}10)`,
                  position:'relative',
                  display:'flex',
                  alignItems:'flex-end',
                  padding:8,
                  border:`1px solid ${job.thumb}25`,
                  overflow:'hidden'
                }}>
                  {clip3Url && (
                    <video
                      src={clip3Url}
                      muted
                      preload="metadata"
                      onLoadedMetadata={(e)=>{
                        const dur = Number(e.currentTarget.duration || 0);
                        if (dur > 0.25) e.currentTarget.currentTime = Math.min(dur * 0.55, 3.0);
                      }}
                      style={{position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover'}}
                    />
                  )}
                  <div style={{position:'absolute', inset:0, background:'linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.35))'}}/>
                  <div style={{position:'absolute', top:8, left:8, padding:'2px 6px', borderRadius:999, background:'rgba(10,12,20,0.65)', color:'#F2C97A', fontSize:10, fontFamily:VT.mono}}>
                    {clipSpeedByIdx[3] ? `${clipSpeedByIdx[3].toFixed(2)}x` : "n/a"}
                  </div>
                  <span style={{fontSize:11, color:'#fff', fontFamily:VT.mono, position:'relative', zIndex:2}}>
                    CLIP 3 · {fmtClipDuration(3)}
                  </span>
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
                {['hard cut','crossfade','dip to black'].map((o) =>
                  <button
                    key={o}
                    onClick={()=>{
                      setSeamType(o);
                      if (o === "hard cut") setXfade(0);
                    }}
                    style={{
                      flex:1, padding:'5px 6px', fontSize:10.5, fontWeight:600, borderRadius:4, border:'none', cursor:'pointer',
                      background: seamType===o ? VT.bg5 : 'transparent',
                      color: seamType===o ? VT.text : VT.textDim
                    }}
                  >
                    {o}
                  </button>
                )}
              </div>
            </div>
            <div>
              <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.8, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Xfade</div>
              <input
                type="range"
                min={0}
                max={1000}
                value={xfade}
                onChange={(e)=>{
                  const next = +e.target.value;
                  setXfade(next);
                  if (next === 0) {
                    setSeamType("hard cut");
                  } else if (seamType === "hard cut") {
                    setSeamType("crossfade");
                  }
                }}
                style={{width:'100%', accentColor:'#9B5CF6'}}
              />
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
            <div style={{fontSize:13, fontWeight:600, color: VT.text}}>Full preview · {job?.aspect_ratio || "9:16"}</div>
            <span style={{fontSize:11, color: VT.textDim, fontFamily:VT.mono}}>
              {assembledVideoUrl ? "Assembled output ready" : `${duration}.{Math.floor(Math.random()*10)}s · 10.8 MB`}
            </span>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'120px 1fr', gap:10, alignItems:'stretch'}}>
            <div style={{minHeight:220}}>
              {fullPreviewUrl ? (
                <video
                  key={fullPreviewUrl}
                  src={fullPreviewUrl}
                  controls
                  preload="metadata"
                  style={{width:'100%', height:'100%', minHeight:220, aspectRatio:previewAspect, borderRadius:10, background:'#000', border:`1px solid ${VT.lineHi}`}}
                />
              ) : (
                <VideoThumb accent={job.thumb} w={'100%'} h={220} playing progress={28} label="play full"/>
              )}
            </div>
            <div style={{display:'flex', flexDirection:'column', gap:8}}>
              <div style={{height:106, borderRadius:10, overflow:'hidden', border:`1px solid ${VT.lineHi}`, background:'#000'}}>
                {seamPreviewUrl ? (
                  <video
                    key={`${seamPreviewUrl}-seam`}
                    src={seamPreviewUrl}
                    controls
                    preload="metadata"
                    style={{width:'100%', height:'100%', objectFit:'cover', background:'#000'}}
                  />
                ) : (
                  <VideoThumb accent={job.thumb} w={'100%'} h={'100%'} playing progress={52} label="CLIP 1 → CLIP 2 seam"/>
                )}
              </div>
              <div style={{height:106, borderRadius:10, overflow:'hidden', border:`1px solid ${VT.lineHi}`, background:'#000'}}>
                {selectedCardUrl ? (
                  <video
                    key={selectedCardUrl}
                    src={selectedCardUrl}
                    controls
                    preload="metadata"
                    style={{width:'100%', height:'100%', objectFit:'cover', background:'#000'}}
                  />
                ) : (
                  <VideoThumb
                    accent="#E8B860"
                    w={'100%'}
                    h={'100%'}
                    label={`END CARD · ${selectedCard?.name || 'select'}`}
                  />
                )}
              </div>
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
            <div key={c.id} onClick={()=>setSelCard((prev)=>prev===c.id ? null : c.id)} style={{
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
          ].map((o) =>
            <button key={o.id} onClick={()=>setRotationPolicy(o.id)} style={{
              flex:1, padding:'7px 4px', fontSize:10.5, fontWeight:600, borderRadius:5,
              border:'none', cursor:'pointer',
              background: rotationPolicy===o.id ? VT.bg5 : 'transparent',
              color: rotationPolicy===o.id ? VT.text : VT.textDim,
              display:'flex', alignItems:'center', justifyContent:'center', gap:4,
            }}>
              {React.createElement(IC[o.ic], {width:11, height:11})} {o.label}
            </button>
          )}
        </div>
        <div style={{fontSize:11, color: VT.textDim, marginTop:10, lineHeight:1.5, padding:10, background:'rgba(232,184,96,0.05)', border:'1px solid rgba(232,184,96,0.2)', borderRadius:7}}>
          {rotationPolicy === "random" && (
            <><b style={{color:'#E8B860'}}>Random</b> — picks a random end card from the pool for this video.</>
          )}
          {rotationPolicy === "round" && (
            <><b style={{color:'#E8B860'}}>Round-robin</b> — next card in pool picked automatically. Override above for this video.</>
          )}
          {rotationPolicy === "campaign" && (
            <><b style={{color:'#E8B860'}}>Campaign</b> — prioritizes cards tagged for the active campaign.</>
          )}
        </div>
      </Panel>
    </div>
  </div>;
}

window.Assembly = Assembly;
