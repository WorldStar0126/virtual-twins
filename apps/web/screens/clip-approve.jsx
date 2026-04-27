// Clip 1 approval gate — this is the heart of the new workflow
const { useState: useStateA, useEffect: useEffectA } = React;

function ClipApprove({ nav, jobId, jobs = [], clients = [], onApproval, onRegenerate, onStop, actingOnJob = false, fetchEvents, fetchJobClips }) {
  const job = jobs.find(j=>j.id===jobId) || jobs[0] || window.JOBS[0];
  const client = clients.find(c=>c.slug===job?.client) || window.CLIENTS.find(c=>c.slug===job?.client);
  const apiBase = window.VTApi?.Api?.base || "";
  const selectedImageRefs = (job?.image_indices && job.image_indices.length > 0)
    ? job.image_indices.map((idx) => `@Image${idx}`)
    : ["@Image1", "@Image2", "@Image3", "@Image4"];
  const selectedAudioRefs = (job?.audio_indices && job.audio_indices.length > 0)
    ? job.audio_indices.map((idx) => `@Audio${idx}`)
    : [];
  const voiceLabel = `${selectedAudioRefs[0] || "@Audio1"} (cloned)`;
  const selectedRefs = [...selectedImageRefs, ...selectedAudioRefs];
  const fallbackLocalUrl = (() => {
    if (!job?.output_path || !job?.client) return null;
    const normalized = String(job.output_path).replaceAll("\\", "/");
    const marker = `/output/${job.client}/`;
    const idx = normalized.indexOf(marker);
    if (idx < 0) return null;
    const rel = normalized.slice(idx + "/output".length);
    return `/output-files${rel}`;
  })();
  const playableUrl = job?.output_local_url
    ? `${apiBase}${job.output_local_url}`
    : fallbackLocalUrl
      ? `${apiBase}${fallbackLocalUrl}`
      : (job?.video_url || null);
  const [playing, setPlaying] = useStateA(false);
  const [progress, setProgress] = useStateA(42);
  const [note, setNote] = useStateA('');
  const [events, setEvents] = useStateA([]);
  const [dirClips, setDirClips] = useStateA([]);
  const [error, setError] = useStateA("");
  const clipGenerating = job?.status === "rendering" && job?.stage === "clip_1_gen";
  const reviewMatch = String(job?.stage || "").match(/^clip_(\d+)_review$/);
  const currentClip = reviewMatch ? Number(reviewMatch[1]) : Math.max(1, Number(job?.clipsDone || 1));
  const isFinalClip = currentClip >= Number(job?.clipsTotal || 2);
  const isAnyGenerating = job?.status === "rendering";
  const isPostFinalApproval = job?.status === "queued" || job?.status === "awaiting_assembly" || job?.stage === "assembly_review" || job?.status === "done";
  const disableDecisionActions = actingOnJob || isAnyGenerating || isPostFinalApproval;
  const disableRejectStop = actingOnJob || isPostFinalApproval;

  const toOutputUrl = (path) => {
    if (!path || !job?.client) return null;
    const normalized = String(path).replaceAll("\\", "/");
    const marker = `/output/${job.client}/`;
    const idx = normalized.indexOf(marker);
    if (idx < 0) return null;
    const rel = normalized.slice(idx + "/output".length);
    return `${apiBase}/output-files${rel}`;
  };

  const clipDownloads = (() => {
    const map = new Map();
    (dirClips || []).forEach((entry) => {
      const clipIdx = Number(entry?.clip);
      if (!clipIdx) return;
      const url = `${apiBase}/v1/jobs/${job.id}/clips/${clipIdx}/stream`;
      if (!url) return;
      map.set(clipIdx, { clip: clipIdx, url, path: entry?.output_path || "" });
    });
    const fromJob = job?.clip_outputs || {};
    Object.values(fromJob).forEach((entry) => {
      const clipIdx = Number(entry?.clip);
      if (!clipIdx) return;
      const url = entry?.output_local_url ? `${apiBase}${entry.output_local_url}` : toOutputUrl(entry?.output_path);
      if (!url) return;
      map.set(clipIdx, { clip: clipIdx, url, path: entry?.output_path || "" });
    });
    (events || []).forEach((evt) => {
      const m = String(evt.type || "").match(/^clip_(\d+)\.downloaded$/);
      if (!m) return;
      const clipIdx = Number(m[1]);
      const path = evt?.meta?.output_path;
      const url = toOutputUrl(path);
      if (!url) return;
      map.set(clipIdx, { clip: clipIdx, url, path });
    });
    return Array.from(map.values()).sort((a, b) => a.clip - b.clip);
  })();

  const currentClipEntry = clipDownloads.find((c) => c.clip === currentClip);
  const activePlayableUrl = currentClipEntry?.url || playableUrl;
  const displaySeed = job?.seed || String(job?.id || "unknown");

  useEffectA(() => {
    let active = true;
    if (!job?.id || !fetchEvents) return undefined;
    const load = async () => {
      try {
        const rows = await fetchEvents(job.id);
        if (active) setEvents(rows || []);
      } catch (err) {
        if (active) setError(err.message || "Failed to load events");
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [job?.id, fetchEvents]);

  useEffectA(() => {
    let active = true;
    if (!job?.id || !fetchJobClips) return undefined;
    const load = async () => {
      try {
        const rows = await fetchJobClips(job.id);
        if (active) setDirClips(rows || []);
      } catch (err) {
        if (active) setError(err.message || "Failed to load clip files");
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [job?.id, fetchJobClips]);

  if (!job || !client) {
    return <div style={{padding:'24px 28px', color:VT.textDim}}>No job available yet. Create a job first.</div>;
  }

  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    {/* Header */}
    <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:18}}>
      <Btn variant="subtle" onClick={()=>nav('dashboard')} style={{paddingLeft:8}}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Back</Btn>
      <div style={{width:1, height:20, background:VT.line}}/>
      <Avatar client={client} size={34}/>
      <div>
        <div style={{fontSize:12, color: VT.textDim}}>{client.name} · {job.template}</div>
        <div style={{fontFamily: VT.display, fontSize:20, fontWeight:600, color: VT.text, letterSpacing:-0.2}}>Clip {currentClip} approval <span style={{color:VT.textMuted, fontFamily: VT.mono, fontSize:14, marginLeft:8}}>{job.id}</span></div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
        <Pill tone="warn"><IC.warn width={11} height={11}/> Approval gated · next stage blocked</Pill>
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
          {activePlayableUrl ? (
            <video
              key={activePlayableUrl || "no-video"}
              src={activePlayableUrl}
              controls
              preload="metadata"
              style={{width:'100%', height:'100%', objectFit:'contain', background:'#000'}}
            />
          ) : (
            <>
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
            </>
          )}

          {/* meta bar */}
          <div style={{position:'absolute', top:14, left:14, right:14, display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
            <div style={{display:'flex', gap:8}}>
              <Pill tone="brand" small>CLIP {currentClip} / {job.clipsTotal}</Pill>
              <Pill tone="neutral" small>{`10.0s · ${job.resolution || '720p'} · ${job.aspect_ratio || '9:16'} · ${job.fast_tier ? 'Fast' : 'Standard'}`}</Pill>
            </div>
            <div style={{fontFamily: VT.mono, fontSize:11, color:'rgba(255,255,255,0.6)'}}>seed: {displaySeed}</div>
          </div>

          {/* Scrubber */}
          {!activePlayableUrl && <div style={{position:'absolute', bottom:0, left:0, right:0, padding:'12px 16px', background:'linear-gradient(180deg, transparent, rgba(0,0,0,0.8))'}}>
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
          </div>}
        </div>

        {/* Prompt recall */}
        <Panel pad={16}>
          <SectionHeader title="What we asked for" eyebrow="Prompt used"/>
          <div style={{padding:12, background: VT.bg4, borderRadius:8, fontSize:12.5, color: VT.textDim, lineHeight:1.6, fontFamily: VT.body}}>
            {job.prompt}
          </div>
          <div style={{display:'flex', gap:6, marginTop:10, flexWrap:'wrap'}}>
            {selectedRefs.map(r =>
              <span key={r} style={{padding:'3px 8px', background:'rgba(155,92,246,0.1)', color:'#B57CF8', fontSize:11, fontFamily:VT.mono, borderRadius:5, border:'1px solid rgba(155,92,246,0.2)'}}>{r}</span>
            )}
            {selectedRefs.length===0 && <span style={{fontSize:11, color:VT.textMuted}}>No explicit references selected</span>}
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
            <Btn variant="brand" icon="check" size="lg" onClick={async ()=>{
              if (!onApproval) return;
              try {
                setError("");
                const updated = await onApproval(job.id, true, note);
                if (updated.status === "queued" || updated.status === "awaiting_assembly" || updated.status === "done") nav("assembly", updated.id);
                else nav("clip-approve", updated.id);
              } catch (err) {
                setError(err.message || "Approval failed");
              }
            }} disabled={disableDecisionActions} style={{flex:1, justifyContent:'center'}}>
              {isAnyGenerating ? "Clip generating..." : actingOnJob ? "Submitting..." : (isFinalClip ? "Approve · go to assembly" : `Approve · fire clip ${currentClip + 1}`)}
            </Btn>
            <Btn
              variant="gold"
              icon="retry"
              size="lg"
              disabled={disableDecisionActions}
              onClick={async ()=>{
                if (!onRegenerate) return;
                try {
                  setError("");
                  await onRegenerate(job.id);
                } catch (err) {
                  setError(err.message || "Regeneration failed");
                }
              }}
              style={{flex:1, justifyContent:'center'}}
            >
              {isAnyGenerating ? "Generating..." : `Regenerate clip ${currentClip}`}
            </Btn>
            <Btn variant="danger" icon="x" size="lg" onClick={async ()=>{
              if (isAnyGenerating) {
                if (!onStop) return;
                try {
                  setError("");
                  await onStop(job.id);
                  nav('dashboard');
                } catch (err) {
                  setError(err.message || "Stop failed");
                }
                return;
              }
              if (!onApproval) return;
              try {
                setError("");
                await onApproval(job.id, false, note);
                nav('dashboard');
              } catch (err) {
                setError(err.message || "Rejection failed");
              }
            }} disabled={disableRejectStop}>Reject & stop</Btn>
          </div>
          {error && <div style={{fontSize:12, color:'#F06571', marginBottom:10}}>{error}</div>}

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
              {l:'Voice',       v:voiceLabel,                      tone:'success'},
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
          <SectionHeader title="Run events" eyebrow={`${events.length} events`}/>
          <div style={{display:'flex', flexDirection:'column', gap:8, maxHeight:220, overflowY:'auto'}}>
            {events.slice().reverse().map(evt => (
              <div key={evt.id} style={{padding:'8px 10px', background:VT.bg4, borderRadius:7}}>
                <div style={{fontSize:10.5, color:VT.textMuted, fontFamily:VT.mono}}>{evt.type}</div>
                <div style={{fontSize:12, color:VT.text, marginTop:2}}>{evt.message}</div>
              </div>
            ))}
            {events.length===0 && <div style={{fontSize:12, color:VT.textMuted}}>No events yet.</div>}
          </div>
        </Panel>
      </div>
    </div>
  </div>;
}

window.ClipApprove = ClipApprove;
