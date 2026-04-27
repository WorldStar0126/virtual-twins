// New video job setup — pick client, format, prompt UX (with 3 prompt UX options)
const { useState: useStateN, useEffect: useEffectN } = React;

function StepChip({ n, active, done, alert, label }) {
  return <div style={{display:'flex', alignItems:'center', gap:10, opacity: active||done||alert?1:0.5}}>
    <div style={{
      width:26, height:26, borderRadius:13,
      background: done ? VT.gradBrand : alert ? 'rgba(240,101,113,0.16)' : active ? 'rgba(155,92,246,0.15)' : VT.bg4,
      border: `1px solid ${done ? 'transparent' : alert ? 'rgba(240,101,113,0.55)' : active ? 'rgba(155,92,246,0.5)' : VT.line}`,
      display:'flex', alignItems:'center', justifyContent:'center',
      fontSize:11, fontWeight:700, color: done ? '#0E0F13' : alert ? '#F06571' : active ? '#B57CF8' : VT.textDim,
      fontFamily: VT.display,
    }}>{done ? <IC.check width={12} height={12}/> : alert ? <IC.warn width={12} height={12}/> : n}</div>
    <span style={{fontSize:12, fontWeight: active||alert?600:500, color: alert?'#F06571': active?VT.text: VT.textDim}}>{label}</span>
  </div>;
}

function JobNew({ nav, clients = [], creatingJob = false, onCreateJob }) {
  const templates = window.TEMPLATES || [];
  const api = window.VTApi?.Api;
  const apiBase = api?.base || "";
  const [client, setClient] = useStateN(clients[1] || clients[0] || null);
  const [format, setFormat] = useStateN('20s');
  const [template, setTemplate] = useStateN(null);
  const [promptUx, setPromptUx] = useStateN('structured'); // structured | freeform | shotlist
  const [freeform, setFreeform] = useStateN("");
  const [promptFields, setPromptFields] = useStateN({
    wardrobe: "",
    setting: "",
    camera: "",
    expression: "",
    dialogue: "",
  });
  const [selectedImgs, setSelectedImgs] = useStateN([]);
  const [selectedAudio, setSelectedAudio] = useStateN([]);
  const [resolution, setResolution] = useStateN("720p");
  const [aspectRatio, setAspectRatio] = useStateN("9:16");
  const [tier, setTier] = useStateN("Standard");
  const [assetsLoading, setAssetsLoading] = useStateN(false);
  const [assetRows, setAssetRows] = useStateN({ images: [], audio: [] });
  const [submitError, setSubmitError] = useStateN("");
  const [stepAlertPulse, setStepAlertPulse] = useStateN(false);

  useEffectN(() => {
    if (!client && clients.length > 0) setClient(clients[0]);
  }, [clients, client]);

  useEffectN(() => {
    let active = true;
    if (!client?.slug || !api?.getClientAssets) return undefined;
    const load = async () => {
      setAssetsLoading(true);
      try {
        const payload = await api.getClientAssets(client.slug);
        if (!active) return;
        const images = payload.images || [];
        const audio = payload.audio || [];
        setAssetRows({ images, audio });
        setSelectedImgs(images.slice(0, 4).map((x) => x.index));
        setSelectedAudio(audio.slice(0, 1).map((x) => x.index));
      } catch (err) {
        if (!active) return;
        setAssetRows({ images: [], audio: [] });
      } finally {
        if (active) setAssetsLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [client?.slug, api]);

  const nClips = format === '20s' ? 2 : 3;
  const tierCost = tier === "Fast" ? 2.5 : 3.0;
  const estCost = (nClips * tierCost).toFixed(2);
  const structuredPrompt = [
    promptFields.wardrobe ? `Wardrobe: ${promptFields.wardrobe}.` : "",
    promptFields.setting ? `Setting: ${promptFields.setting}.` : "",
    promptFields.camera ? `Camera: ${promptFields.camera}.` : "",
    promptFields.expression ? `Expression: ${promptFields.expression}.` : "",
    promptFields.dialogue ? `Dialogue: ${promptFields.dialogue}.` : "",
  ].filter(Boolean).join(" ");
  const resolvedPrompt = promptUx === "freeform" ? freeform.trim() : structuredPrompt.trim();
  const isPromptValid = resolvedPrompt.length > 0;
  const isClientValid = Boolean(client?.slug);
  const isTemplateValid = Boolean(template?.id);
  const hasPhotoRef = selectedImgs.length > 0;
  const hasAudioRef = selectedAudio.length > 0;
  const canGenerate = isClientValid && isPromptValid && hasPhotoRef;
  const isStep1Done = isClientValid && Boolean(format);
  const isStep2Done = isPromptValid; // template is optional
  const isStep3Done = hasPhotoRef; // audio is optional
  const isStep4Done = canGenerate;
  const showStepAlerts = stepAlertPulse && !canGenerate;
  const dismissStepAlerts = () => {
    if (stepAlertPulse) setStepAlertPulse(false);
  };
  const firstIncompleteStep =
    !isStep1Done ? 1 :
    !isStep2Done ? 2 :
    !isStep3Done ? 3 :
    !isStep4Done ? 4 : 4;
  const streamJobEventsToConsole = (jobId) => {
    if (!api?.getEvents || !jobId) return;
    const seen = new Set();
    let attempts = 0;
    const maxAttempts = 20; // ~60s total
    const timer = setInterval(async () => {
      attempts += 1;
      try {
        const events = await api.getEvents(jobId);
        (events || []).forEach((evt) => {
          if (seen.has(evt.id)) return;
          seen.add(evt.id);
          console.log(`[job:${jobId}] ${evt.type} - ${evt.message}`, evt.meta || {});
        });
        const done = (events || []).some((evt) => evt.type === "job.completed" || evt.type === "job.failed");
        if (done || attempts >= maxAttempts) clearInterval(timer);
      } catch (err) {
        console.warn(`[job:${jobId}] event polling error`, err);
        if (attempts >= maxAttempts) clearInterval(timer);
      }
    }, 3000);
  };

  return <div
    style={{padding:'24px 28px', maxWidth:1480, margin:'0 auto'}}
    onMouseDownCapture={dismissStepAlerts}
    onKeyDownCapture={dismissStepAlerts}
    onInputCapture={dismissStepAlerts}
  >
    {/* Header */}
    <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:20}}>
      <Btn variant="subtle" icon="chev" onClick={()=>nav('dashboard')} style={{transform:'rotate(180deg)', paddingLeft:8}}/>
      <div>
        <div style={{fontSize:11, color: VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600}}>New job</div>
        <div style={{fontFamily: VT.display, fontSize:24, fontWeight:600, color: VT.text, letterSpacing:-0.3}}>Generate video</div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:10, alignItems:'center'}}>
        <div style={{fontSize:11, color: VT.textDim}}>Est. total: <b className="vt-gold-text" style={{fontSize:13}}>${estCost}</b> · {nClips} clips</div>
        <Btn variant="ghost">Save draft</Btn>
        <Btn
          variant="primary"
          icon="bolt"
          onClick={async ()=>{
            if (!onCreateJob) return;
            if (!canGenerate) {
              setStepAlertPulse(true);
              setSubmitError("");
              return;
            }
            try {
              setSubmitError("");
              console.log("[generate] submitting job payload", {
                client_slug: client.slug,
                format,
                resolution,
                aspect_ratio: aspectRatio,
                fast_tier: tier === "Fast",
                image_indices: selectedImgs,
                audio_indices: selectedAudio,
                template: template?.name || "Custom / Freeform",
              });
              const newJob = await onCreateJob({
                client_slug: client.slug,
                prompt: resolvedPrompt || "Client-facing short-form promotional video.",
                format,
                resolution,
                aspect_ratio: aspectRatio,
                fast_tier: tier === "Fast",
                image_indices: selectedImgs,
                audio_indices: selectedAudio,
                template: template?.name || "Custom / Freeform",
              });
              console.log(`[generate] job created: ${newJob.id}`);
              streamJobEventsToConsole(newJob.id);
              nav('clip-approve', newJob.id);
            } catch (err) {
              setSubmitError(err.message || "Failed to create job");
            }
          }}
          disabled={creatingJob}
        >
          {creatingJob ? "Creating..." : "Generate clip 1"}
        </Btn>
      </div>
    </div>
    {submitError && <div style={{marginBottom:14, color:'#F06571', fontSize:12}}>{submitError}</div>}

    {/* Stepper */}
    <div style={{display:'flex', gap:26, alignItems:'center', marginBottom:22, paddingBottom:18, borderBottom:`1px solid ${VT.line}`}}>
      <StepChip n={1} label="Client & format" active={firstIncompleteStep===1 && !isStep1Done} done={isStep1Done} alert={showStepAlerts && !isStep1Done}/>
      <div style={{width:24, height:1, background:VT.line}}/>
      <StepChip n={2} label="Template & prompt" active={firstIncompleteStep===2 && !isStep2Done} done={isStep2Done} alert={showStepAlerts && !isStep2Done}/>
      <div style={{width:24, height:1, background:VT.line}}/>
      <StepChip n={3} label="References" active={firstIncompleteStep===3 && !isStep3Done} done={isStep3Done} alert={showStepAlerts && !isStep3Done}/>
      <div style={{width:24, height:1, background:VT.line}}/>
      <StepChip n={4} label="Review & fire" active={firstIncompleteStep===4 && !isStep4Done} done={isStep4Done} alert={showStepAlerts && !isStep4Done}/>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'1fr 360px', gap:20, alignItems:'flex-start'}}>
      {/* Main column */}
      <div style={{display:'flex', flexDirection:'column', gap:16}}>
        {/* Client + format */}
        <Panel pad={18}>
          <SectionHeader title="Client & format" eyebrow="Step 1"/>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:14}}>
            {/* Client picker */}
            <div>
              <div style={{fontSize:11, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Client</div>
              <div style={{display:'flex', flexDirection:'column', gap:4, maxHeight:200, overflowY:'auto', paddingRight:4}}>
                {clients.map(c =>
                  <div key={c.slug} onClick={()=>setClient(c)} style={{
                    display:'flex', alignItems:'center', gap:10, padding:'8px 10px',
                    borderRadius:8, cursor:'pointer',
                    background: client?.slug===c.slug ? 'rgba(155,92,246,0.1)' : 'transparent',
                    border: `1px solid ${client?.slug===c.slug ? 'rgba(155,92,246,0.3)' : 'transparent'}`,
                  }}>
                    <Avatar client={c} size={30}/>
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontSize:12.5, fontWeight:600, color: VT.text}}>{c.name}</div>
                      <div style={{fontSize:10.5, color: VT.textMuted}}>{c.company} · {c.market}</div>
                    </div>
                    {client?.slug===c.slug && <IC.check width={14} height={14} style={{color:'#B57CF8'}}/>}
                  </div>
                )}
              </div>
            </div>

            {/* Format picker */}
            <div>
              <div style={{fontSize:11, color: VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600, marginBottom:8}}>Duration format</div>
              <div style={{display:'flex', flexDirection:'column', gap:10}}>
                {[
                  {id:'20s', label:'20 seconds', sub:'2 clips × 10s + 3s end card = 23s delivered', cost:'~$6.00', rec: true},
                  {id:'30s', label:'30 seconds', sub:'3 clips × 10s + 3s end card = 33s delivered', cost:'~$9.00', rec: false},
                ].map(f =>
                  <div key={f.id} onClick={()=>setFormat(f.id)} style={{
                    padding:14, borderRadius:10, cursor:'pointer',
                    background: format===f.id ? 'rgba(232,184,96,0.06)' : VT.bg3,
                    border: `1px solid ${format===f.id ? 'rgba(232,184,96,0.35)' : VT.line}`,
                    position:'relative',
                  }}>
                    {f.rec && <div style={{position:'absolute', top:8, right:10}}><Pill tone="gold" small>Default</Pill></div>}
                    <div style={{display:'flex', alignItems:'baseline', gap:10, marginBottom:4}}>
                      <div style={{fontFamily: VT.display, fontSize:18, fontWeight:600, color: VT.text}}>{f.label}</div>
                      <div style={{fontSize:11, color: VT.textMuted, fontFamily: VT.mono}}>{f.cost}</div>
                    </div>
                    <div style={{fontSize:11.5, color: VT.textDim}}>{f.sub}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Panel>

        {/* Template picker */}
        <Panel pad={18}>
          <SectionHeader title="Template" eyebrow="Step 2 · pick a content type"/>
          <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:8}}>
            {templates.filter(t=>!client || t.industries.includes(client.industry)||t.id==='t_custom').map(t =>
              <div key={t.id} onClick={()=>setTemplate(template?.id===t.id ? null : t)} style={{
                padding:'14px 12px', borderRadius:10, cursor:'pointer',
                background: template?.id===t.id ? 'rgba(155,92,246,0.08)' : VT.bg3,
                border:`1px solid ${template?.id===t.id ? 'rgba(155,92,246,0.35)' : VT.line}`,
                textAlign:'center',
              }}>
                <div style={{width:36, height:36, borderRadius:8, margin:'0 auto 8px',
                  background:'rgba(155,92,246,0.1)', display:'flex', alignItems:'center', justifyContent:'center',
                  color: template?.id===t.id ? '#B57CF8' : VT.textDim,
                }}>{React.createElement(IC[t.icon]||IC.film, {width:16, height:16})}</div>
                <div style={{fontSize:11.5, fontWeight:600, color: VT.text, marginBottom:2}}>{t.name}</div>
                <div style={{fontSize:10, color: VT.textMuted}}>{t.duration}</div>
              </div>
            )}
          </div>
        </Panel>

        {/* Prompt UX — 3 options */}
        <Panel pad={18}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16}}>
            <SectionHeader title="Prompt" eyebrow="Step 3 · tell the model what to make"/>
            <div style={{display:'flex', gap:4, padding:3, background: VT.bg4, borderRadius:8, border:`1px solid ${VT.line}`}}>
              {[
                {id:'structured', label:'Structured', ic:'layers'},
                {id:'freeform',   label:'Freeform', ic:'wand'},
                {id:'shotlist',   label:'Shot list', ic:'film'},
              ].map(m =>
                <button key={m.id} onClick={()=>setPromptUx(m.id)} style={{
                  display:'flex', alignItems:'center', gap:6,
                  padding:'6px 11px', borderRadius:5,
                  background: promptUx===m.id ? VT.bg3 : 'transparent',
                  color: promptUx===m.id ? VT.text : VT.textDim,
                  border:'none', cursor:'pointer', fontSize:11, fontWeight:600,
                  boxShadow: promptUx===m.id ? '0 1px 4px rgba(0,0,0,0.3)' : 'none',
                }}>
                  {React.createElement(IC[m.ic], {width:12, height:12})} {m.label}
                </button>
              )}
            </div>
          </div>

          {promptUx==='freeform' && (
            <div>
              <textarea value={freeform} onChange={e=>setFreeform(e.target.value)}
                placeholder='Example: James walks through a modern staged living room, stops, turns to camera and says "This 3-bed in Smithfield just hit market - and it will not last." Golden hour light, dolly in. @Image1 @Image2 @Image3 @Audio1 as references.'
                style={{
                  width:'100%', minHeight:180, padding:14,
                  background: VT.bg4, border:`1px solid ${VT.line}`, borderRadius:10,
                  color: VT.text, fontFamily: VT.body, fontSize:13, lineHeight:1.55,
                  resize:'vertical', outline:'none',
                }}/>
              <div style={{display:'flex', gap:8, marginTop:10, flexWrap:'wrap'}}>
                {['Add wardrobe detail','Specify lighting','Add camera move','Add dialogue','Add @Image refs'].map(t =>
                  <button key={t} style={{padding:'5px 10px', borderRadius:6, fontSize:11, background:VT.bg4, border:`1px solid ${VT.line}`, color: VT.textDim, cursor:'pointer', display:'flex', alignItems:'center', gap:5}}>
                    <IC.sparkle width={11} height={11} style={{color:'#B57CF8'}}/> {t}
                  </button>
                )}
              </div>
            </div>
          )}

          {promptUx==='structured' && (
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
              {[
                {l:'Wardrobe', v:'Charcoal suit, open-collar white shirt', ph:'What client wears'},
                {l:'Setting', v:'Modern staged living room, golden hour', ph:'Location, time of day'},
                {l:'Camera', v:'Slow dolly in, handheld feel, shallow DoF', ph:'Movement, lens, grade'},
                {l:'Expression', v:'Confident smile, direct eye contact', ph:'Mood, energy'},
                {l:'Dialogue', v:'"This 3-bed in Smithfield just hit market — and it won\'t last."', ph:'Exact words', span:2},
              ].map(f =>
                <div key={f.l} style={{gridColumn: f.span?'span 2':'auto'}}>
                  <div style={{fontSize:10.5, color: VT.textMuted, letterSpacing:.8, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>{f.l}</div>
                  <input
                    value={promptFields[f.l.toLowerCase()] || ""}
                    onChange={e=>setPromptFields((prev)=>({...prev, [f.l.toLowerCase()]: e.target.value}))}
                    placeholder={f.v}
                    style={{
                    width:'100%', padding:'10px 12px',
                    background: VT.bg4, border:`1px solid ${VT.line}`, borderRadius:8,
                    color: VT.text, fontFamily: VT.body, fontSize:12.5, outline:'none',
                  }}/>
                </div>
              )}
            </div>
          )}

          {promptUx==='shotlist' && (
            <div style={{display:'flex', flexDirection:'column', gap:10}}>
              {[
                {n:1, dur:'10s', desc:'Wide: James walks into staged living room, hand in pocket, pauses by sofa.'},
                {n:2, dur:'10s', desc:'Medium CU: James turns to camera, smiles, delivers line with confidence.'},
                ...(format==='30s' ? [{n:3, dur:'10s', desc:'Exterior: James steps out onto porch, nods to camera, thumbs-up.'}] : []),
              ].map(s =>
                <div key={s.n} style={{
                  display:'grid', gridTemplateColumns:'44px 70px 1fr auto',
                  alignItems:'center', gap:12,
                  padding:'10px 14px', background: VT.bg4,
                  border:`1px solid ${VT.line}`, borderRadius:10,
                }}>
                  <div style={{fontFamily: VT.display, fontSize:22, fontWeight:700, color:'#B57CF8'}}>0{s.n}</div>
                  <Pill tone="brand" small>{s.dur}</Pill>
                  <input placeholder={s.desc} style={{
                    background:'transparent', border:'none', outline:'none',
                    color: VT.text, fontSize:12.5, fontFamily: VT.body,
                  }}/>
                  <IC.dots width={14} height={14} style={{color:VT.textMuted, cursor:'pointer'}}/>
                </div>
              )}
              <div style={{
                padding:'10px 14px', borderRadius:10,
                background:'rgba(155,92,246,0.04)',
                border:`1px dashed rgba(155,92,246,0.2)`,
                fontSize:11.5, color: VT.textDim, fontStyle:'italic',
              }}>
                <b style={{color:'#B57CF8'}}>Shared style block</b> — applied to every clip: same wardrobe, lighting, grade. Edit to override.
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* Right sidebar — references & summary */}
      <div style={{display:'flex', flexDirection:'column', gap:14, position:'sticky', top:20}}>
        <Panel pad={16}>
          <SectionHeader title="References" eyebrow="Step 4 · pick 3-4"
            action={<span style={{fontSize:11, color:'#F2C97A'}}>{selectedImgs.length} photos · {selectedAudio.length} audio</span>}/>
          <div style={{fontSize:11, color: VT.textDim, marginBottom:10, lineHeight:1.5}}>Cost lever: 3-4 images recommended. Going to 8 jumped cost from $3 → $10 in past runs.</div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:6}}>
            {assetRows.images.map((img) => {
              const n = img.index;
              const sel = selectedImgs.includes(n);
              return <div key={n} onClick={()=>setSelectedImgs(sel? selectedImgs.filter(x=>x!==n): [...selectedImgs, n])}
                style={{
                  aspectRatio:'1', borderRadius:6, cursor:'pointer',
                  background: `linear-gradient(${n*45}deg, ${(client?.color || '#9B5CF6')}40, ${(client?.color || '#9B5CF6')}15)`,
                  border: `2px solid ${sel ? (client?.color || '#9B5CF6') : 'transparent'}`,
                  position:'relative', overflow:'hidden',
                }}>
                <img src={`${apiBase}${img.local_url}`} alt={img.file} loading="lazy" style={{width:'100%', height:'100%', objectFit:'cover'}}/>
                {sel && <div style={{position:'absolute', top:2, right:2, width:14, height:14, borderRadius:7, background: client?.color || '#9B5CF6', display:'flex', alignItems:'center', justifyContent:'center'}}>
                  <IC.check width={9} height={9} style={{color:'#000'}}/>
                </div>}
                <div style={{position:'absolute', bottom:2, left:4, fontSize:9, fontFamily:VT.mono, color:'rgba(255,255,255,0.6)'}}>@Image{n}</div>
              </div>;
            })}
          </div>
          {!assetsLoading && assetRows.images.length===0 && <div style={{fontSize:11, color:VT.textMuted, marginTop:8}}>No photos available for this client yet.</div>}
          <div style={{marginTop:14, padding:10, background: VT.bg4, borderRadius:8, fontSize:11, color: VT.textDim, display:'flex', alignItems:'center', gap:8}}>
            <IC.bolt width={13} height={13} style={{color:'#E8B860'}}/>
            <span>Suggested by model: <b style={{color:VT.text}}>front, L profile, R profile, full body</b></span>
          </div>
        </Panel>

        <Panel pad={16}>
          <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, marginBottom:12}}>Audio reference</div>
          <div style={{display:'flex', flexDirection:'column', gap:8}}>
            {assetRows.audio.map((track)=> {
              const selected = selectedAudio.includes(track.index);
              return <div key={track.file} onClick={()=>setSelectedAudio(selected ? selectedAudio.filter((x)=>x!==track.index) : [...selectedAudio, track.index])} style={{display:'flex', alignItems:'center', gap:10, padding:10, background:VT.bg4, borderRadius:8, border:`1px solid ${selected ? '#E8B86055' : 'transparent'}`, cursor:'pointer'}}>
                <div style={{width:32, height:32, borderRadius:16, background:'rgba(232,184,96,0.15)', display:'flex', alignItems:'center', justifyContent:'center'}}>
                  <IC.play width={14} height={14} style={{color:'#E8B860'}}/>
                </div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:12, fontWeight:600, color: VT.text}}>{track.file}</div>
                  <div style={{fontSize:10.5, color: VT.textMuted, fontFamily: VT.mono}}>@Audio{track.index}</div>
                </div>
                {selected && <Pill tone="gold" small>selected</Pill>}
              </div>;
            })}
            {!assetsLoading && assetRows.audio.length===0 && <div style={{fontSize:11, color:VT.textMuted}}>No audio references available for this client.</div>}
          </div>
        </Panel>

        <Panel pad={16}>
          <div style={{fontSize:10, color: VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, marginBottom:12}}>Render settings</div>
          <div style={{display:'flex', flexDirection:'column', gap:10}}>
            {[
              {l:'Resolution', v:resolution, opts:['480p','720p'], set:setResolution},
              {l:'Aspect', v:aspectRatio, opts:['9:16','1:1','16:9','4:3','3:4'], set:setAspectRatio},
              {l:'Tier', v:tier, opts:['Fast','Standard'], set:setTier},
            ].map(r =>
              <div key={r.l} style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
                <span style={{fontSize:11.5, color: VT.textDim}}>{r.l}</span>
                <div style={{display:'flex', gap:3, padding:2, background: VT.bg4, borderRadius:6}}>
                  {r.opts.map(o =>
                    <button key={o} onClick={()=>r.set(o)} style={{
                      padding:'3px 9px', fontSize:10.5, fontWeight:600, borderRadius:4,
                      border:'none', cursor:'pointer',
                      background: r.v===o ? VT.bg5 : 'transparent',
                      color: r.v===o ? VT.text : VT.textDim,
                    }}>{o}</button>
                  )}
                </div>
              </div>
            )}
          </div>
        </Panel>

        <div style={{
          padding:14, borderRadius:10,
          background:'linear-gradient(135deg, rgba(155,92,246,0.06), rgba(232,184,96,0.04))',
          border:`1px solid ${VT.lineBrand}`,
        }}>
          <div style={{fontSize:11, color:'#E8B860', fontWeight:600, letterSpacing:1, textTransform:'uppercase', marginBottom:8, display:'flex', alignItems:'center', gap:6}}>
            <IC.warn width={12} height={12}/> Approval gate
          </div>
          <div style={{fontSize:12, color: VT.text, lineHeight:1.5}}>
            Clip 1 will render first (~$3). You'll review before clips 2{format==='30s'?'/3':''} run — saves ${(nClips-1)*3} if clip 1 is off.
          </div>
        </div>
      </div>
    </div>
  </div>;
}

window.JobNew = JobNew;
