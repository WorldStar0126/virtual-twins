// Remaining screens — assets, endcards, history, cost (compact versions)
const { useState: useStateR } = React;

// ── ASSETS VAULT ─────────────────────────────────────────────
function AssetsVault({ nav, clientSlug, clients = [] }) {
  const { useEffect: useEffectR, useRef: useRefR } = React;
  const client = clients.find(c=>c.slug===clientSlug) || CLIENTS.find(c=>c.slug===clientSlug) || clients[0] || CLIENTS[0];
  const [tab, setTab] = useStateR('photos');
  const [assetsData, setAssetsData] = useStateR({ images: [], audio: [], branding: null });
  const [loading, setLoading] = useStateR(false);
  const [error, setError] = useStateR("");
  const [uploading, setUploading] = useStateR(false);
  const [visiblePhotoCount, setVisiblePhotoCount] = useStateR(8);
  const [selectedPhotos, setSelectedPhotos] = useStateR([]);
  const [selectedAudio, setSelectedAudio] = useStateR([]);
  const [selectedBrandAssets, setSelectedBrandAssets] = useStateR([]);
  const api = window.VTApi?.Api;
  const apiBase = api?.base || "";
  const photoInputRef = useRefR(null);
  const audioInputRef = useRefR(null);
  const brandingInputRef = useRefR(null);
  const logoInputRef = useRefR(null);

  const loadAssets = async (activeGuard = { current: true }) => {
    if (!client?.slug || !api?.getClientAssets) return;
      setLoading(true);
      try {
        const payload = await api.getClientAssets(client.slug);
        if (!activeGuard.current) return;
        setAssetsData({
          images: payload.images || [],
          audio: payload.audio || [],
          branding: payload.branding || null,
        });
        setError("");
      } catch (err) {
        if (!activeGuard.current) return;
        setError(err.message || "Failed to load client assets");
      } finally {
        if (activeGuard.current) setLoading(false);
      }
  };

  useEffectR(() => {
    const guard = { current: true };
    loadAssets(guard);
    return () => {
      guard.current = false;
    };
  }, [client?.slug]);

  const uploadAsset = async (assetType, file) => {
    if (!client?.slug || !file || !api?.uploadClientAsset) return;
    setUploading(true);
    try {
      await api.uploadClientAsset(client.slug, assetType, file);
      await loadAssets({ current: true });
      setError("");
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const deleteAsset = async (assetType, fileName = "") => {
    if (!client?.slug || !api?.deleteClientAsset) return;
    setUploading(true);
    try {
      await api.deleteClientAsset(client.slug, assetType, fileName);
      await loadAssets({ current: true });
      setSelectedPhotos((prev) => prev.filter((name) => name !== fileName));
      setSelectedAudio((prev) => prev.filter((name) => name !== fileName));
      setError("");
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setUploading(false);
    }
  };

  const brandColors = assetsData.branding?.colors || {};
  const brandPrimary = brandColors.primary?.hex || client.brandPrimary;
  const brandAccent = brandColors.accent?.hex || client.brandAccent;
  const logoUrl = assetsData.branding?.logo_light_url ? `${apiBase}${assetsData.branding.logo_light_url}` : null;
  const audioRows = assetsData.audio || [];
  const imageRows = assetsData.images || [];
  const visibleImages = imageRows.slice(0, visiblePhotoCount);
  const logoFile = assetsData.branding?.logo_light_url?.split("/").pop() || "";
  const brandSelections = selectedBrandAssets.length;

  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{display:'flex', alignItems:'center', gap:14, marginBottom:20}}>
      <Btn variant="subtle" onClick={()=>nav('dashboard')}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Roster</Btn>
      <div style={{width:1, height:24, background:VT.line}}/>
      <Avatar client={client} size={44}/>
      <div>
        <div style={{fontFamily:VT.display, fontSize:22, fontWeight:600, color:VT.text, letterSpacing:-0.3}}>{client.name}</div>
        <div style={{fontSize:12, color:VT.textDim, marginTop:2}}>{client.company} · {client.market} · <span style={{color:VT.textMuted}}>synced from {client.assetDrive}</span></div>
      </div>
      <div style={{marginLeft:'auto', display:'flex', gap:8}}>
        <Btn variant="ghost" icon="drive">Open in Drive</Btn>
        <Btn variant="primary" icon="plus" onClick={()=>nav('job-new')}>New video</Btn>
      </div>
    </div>

    {/* Tabs */}
    <div style={{display:'flex', gap:4, marginBottom:16, borderBottom:`1px solid ${VT.line}`}}>
      {[
        {id:'photos', label:`Photos · ${imageRows.length}`, ic:'cards'},
        {id:'audio',  label:`Audio · ${audioRows.length}`,  ic:'film'},
        {id:'brand',  label:'Brand kit', ic:'sparkle'},
        {id:'settings', label:'Settings', ic:'user'},
      ].map(t =>
        <button key={t.id} onClick={()=>setTab(t.id)} style={{
          display:'flex', alignItems:'center', gap:8,
          padding:'10px 16px', background:'transparent', border:'none',
          borderBottom: `2px solid ${tab===t.id ? '#B57CF8' : 'transparent'}`,
          color: tab===t.id ? VT.text : VT.textDim,
          fontSize: 12.5, fontWeight:600, cursor:'pointer',
          marginBottom: -1,
        }}>
          {React.createElement(IC[t.ic], {width:13, height:13})} {t.label}
        </button>
      )}
    </div>

    {tab==='photos' && <>
      <div style={{display:'flex', justifyContent:'flex-end', marginBottom:12}}>
        <input
          ref={photoInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp"
          style={{display:'none'}}
          onChange={(e)=>uploadAsset("photo", e.target.files?.[0])}
        />
        <Btn variant="primary" icon="upload" onClick={()=>photoInputRef.current?.click()}>{uploading ? "Uploading..." : "Upload photo"}</Btn>
        <div style={{width:8}}/>
        <Btn
          variant="danger"
          icon="x"
          onClick={async ()=>{
            for (const name of selectedPhotos) {
              // eslint-disable-next-line no-await-in-loop
              await deleteAsset("photo", name);
            }
            setSelectedPhotos([]);
          }}
          disabled={uploading || selectedPhotos.length===0}
        >
          Delete selected ({selectedPhotos.length})
        </Btn>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:12}}>
      {visibleImages.map((image) =>
        <div
          key={image.file}
          onClick={()=>setSelectedPhotos((prev)=>prev.includes(image.file)?prev.filter((n)=>n!==image.file):[...prev,image.file])}
          style={{cursor:'pointer'}}
        >
        <Panel
          pad={0}
          style={{overflow:'hidden', border:selectedPhotos.includes(image.file)?'1px solid #F06571':'1px solid transparent'}}
        >
          <div style={{aspectRatio:'1', background:`linear-gradient(140deg, ${client.color}30, ${client.color}12 60%, #0A0B0F)`, position:'relative'}}>
            <img src={`${apiBase}${image.local_url}`} alt={image.file} loading="lazy" decoding="async" style={{width:'100%', height:'100%', objectFit:'cover'}}/>
            <div style={{position:'absolute', top:8, left:8}}><Pill tone="brand" small>@Image{image.index}</Pill></div>
            {selectedPhotos.includes(image.file) && <div style={{position:'absolute', top:8, right:8}}><Pill tone="danger" small>Selected</Pill></div>}
          </div>
          <div style={{padding:12}}>
            <div style={{fontSize:12, fontWeight:600, color:VT.text, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{image.file}</div>
            <div style={{fontSize:10.5, color: VT.textMuted, fontFamily: VT.mono, marginTop:3}}>
              {image.url ? "fal CDN linked" : "local only"}
            </div>
          </div>
        </Panel>
        </div>
      )}
      {!loading && imageRows.length===0 && <Panel pad={16}><div style={{fontSize:12, color:VT.textMuted}}>No photos found for this client.</div></Panel>}
      </div>
      {imageRows.length > visiblePhotoCount && (
        <div style={{display:'flex', justifyContent:'center', marginTop:12}}>
          <Btn variant="ghost" onClick={()=>setVisiblePhotoCount(c=>c+8)}>Show more photos</Btn>
        </div>
      )}
    </>}

    {tab==='audio' && <>
      <div style={{display:'flex', justifyContent:'flex-end', marginBottom:12}}>
        <input
          ref={audioInputRef}
          type="file"
          accept=".mp3,.wav,.m4a"
          style={{display:'none'}}
          onChange={(e)=>uploadAsset("audio", e.target.files?.[0])}
        />
        <Btn variant="primary" icon="upload" onClick={()=>audioInputRef.current?.click()}>{uploading ? "Uploading..." : "Upload audio"}</Btn>
        <div style={{width:8}}/>
        <Btn
          variant="danger"
          icon="x"
          onClick={async ()=>{
            for (const name of selectedAudio) {
              // eslint-disable-next-line no-await-in-loop
              await deleteAsset("audio", name);
            }
            setSelectedAudio([]);
          }}
          disabled={uploading || selectedAudio.length===0}
        >
          Delete selected ({selectedAudio.length})
        </Btn>
      </div>
      <Panel pad={16}>
      {audioRows.map((track) =>
        <div
          key={track.file}
          onClick={()=>setSelectedAudio((prev)=>prev.includes(track.file)?prev.filter((n)=>n!==track.file):[...prev,track.file])}
          style={{
            display:'flex', alignItems:'center', gap:14, padding:14, background: VT.bg4, borderRadius:10, marginBottom:10,
            border:selectedAudio.includes(track.file)?'1px solid #F06571':'1px solid transparent', cursor:'pointer'
          }}
        >
          <div style={{width:40, height:40, borderRadius:20, background:'rgba(232,184,96,0.15)', display:'flex', alignItems:'center', justifyContent:'center'}}>
            <IC.play width={16} height={16} style={{color:'#E8B860'}}/>
          </div>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:600, color:VT.text}}>{track.file} <Pill tone="brand" small>@Audio{track.index}</Pill></div>
            <div style={{fontSize:11, color:VT.textMuted, fontFamily:VT.mono, marginTop:4}}>
              {track.url ? "fal CDN linked" : "local only"}
            </div>
            <audio
              controls
              preload="none"
              src={`${apiBase}${track.local_url}`}
              style={{marginTop:10, width:'100%'}}
              onClick={(e)=>e.stopPropagation()}
            />
          </div>
          <Pill tone="success" small>indexed</Pill>
        </div>
      )}
      {!loading && audioRows.length===0 && <div style={{fontSize:12, color:VT.textMuted}}>No audio found for this client.</div>}
      </Panel>
    </>}

    {tab==='brand' && <>
      <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginBottom:12}}>
        <input
          ref={brandingInputRef}
          type="file"
          accept=".json"
          style={{display:'none'}}
          onChange={(e)=>uploadAsset("branding", e.target.files?.[0])}
        />
        <input
          ref={logoInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.svg"
          style={{display:'none'}}
          onChange={(e)=>uploadAsset("logo", e.target.files?.[0])}
        />
        <Btn variant="ghost" icon="upload" onClick={()=>brandingInputRef.current?.click()}>{uploading ? "Uploading..." : "Upload branding.json"}</Btn>
        <Btn variant="primary" icon="upload" onClick={()=>logoInputRef.current?.click()}>{uploading ? "Uploading..." : "Upload logo"}</Btn>
        <Btn
          variant="danger"
          icon="x"
          onClick={async ()=>{
            for (const key of selectedBrandAssets) {
              // eslint-disable-next-line no-await-in-loop
              if (key === "branding") await deleteAsset("branding");
              // eslint-disable-next-line no-await-in-loop
              if (key === "logo" && logoFile) await deleteAsset("logo", logoFile);
            }
            setSelectedBrandAssets([]);
          }}
          disabled={uploading || brandSelections===0}
        >
          Delete selected ({brandSelections})
        </Btn>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:14}}>
      <div style={{cursor:'pointer'}} onClick={()=>setSelectedBrandAssets((prev)=>prev.includes("branding")?prev.filter((x)=>x!=="branding"):[...prev,"branding"])}>
      <Panel pad={16} style={{border:selectedBrandAssets.includes("branding")?'1px solid #F06571':'1px solid transparent'}}>
        <SectionHeader title="Brand colors" eyebrow="End card palette"/>
        <div style={{display:'flex', gap:10, marginBottom:14}}>
          <div style={{flex:1, aspectRatio:'1.6', borderRadius:8, background: client.brandPrimary, display:'flex', alignItems:'flex-end', padding:10}}>
            <div>
              <div style={{fontSize:10, color:'rgba(255,255,255,0.6)', letterSpacing:1, textTransform:'uppercase', fontWeight:600}}>Primary</div>
              <div style={{fontFamily: VT.mono, fontSize:11, color:'#fff'}}>{brandPrimary}</div>
            </div>
          </div>
          <div style={{flex:1, aspectRatio:'1.6', borderRadius:8, background: brandAccent, display:'flex', alignItems:'flex-end', padding:10}}>
            <div>
              <div style={{fontSize:10, color:'rgba(255,255,255,0.6)', letterSpacing:1, textTransform:'uppercase', fontWeight:600}}>Accent</div>
              <div style={{fontFamily: VT.mono, fontSize:11, color:'#fff'}}>{brandAccent}</div>
            </div>
          </div>
        </div>
        <div style={{fontSize:11, color:VT.textMuted}}>Source: branding.json {selectedBrandAssets.includes("branding") ? "· selected" : ""}</div>
      </Panel>
      </div>
      <div style={{cursor:'pointer'}} onClick={()=>setSelectedBrandAssets((prev)=>prev.includes("logo")?prev.filter((x)=>x!=="logo"):[...prev,"logo"])}>
      <Panel pad={16} style={{border:selectedBrandAssets.includes("logo")?'1px solid #F06571':'1px solid transparent'}}>
        <SectionHeader title="Logo" eyebrow="Used on end cards"/>
        <div style={{aspectRatio:'2.4', background: brandPrimary, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center'}}>
          {logoUrl ? (
            <img src={logoUrl} alt={`${client.slug} logo`} style={{maxHeight:'80%', maxWidth:'90%', objectFit:'contain'}}/>
          ) : (
            <div style={{fontFamily: VT.display, fontWeight:700, fontSize:22, color: brandAccent, letterSpacing: 1}}>{client.company.toUpperCase()}</div>
          )}
        </div>
        <div style={{fontSize:11, color:VT.textMuted, marginTop:8}}>
          {logoFile ? `File: ${logoFile}` : "No logo file"} {selectedBrandAssets.includes("logo") ? "· selected" : ""}
        </div>
      </Panel>
      </div>
      </div>
    </>}

    {tab==='settings' && <Panel pad={18} style={{maxWidth:720}}>
      <SectionHeader title="Client settings" eyebrow="Billing & defaults"/>
      {[
        {l:'Tier', v:client.tier},
        {l:'Monthly quota', v:`${client.videoQuota} videos`},
        {l:'Default format', v:client.format},
        {l:'Billing contact', v:assetsData.branding?.contact?.email || `billing@${client.company.toLowerCase().replace(/[^a-z]/g,'')}.com`},
        {l:'Asset sync', v:client.assetDrive},
      ].map(r =>
        <div key={r.l} style={{display:'flex', justifyContent:'space-between', padding:'12px 0', borderBottom:`1px solid ${VT.line}`}}>
          <span style={{fontSize:12, color:VT.textDim}}>{r.l}</span>
          <span style={{fontSize:12.5, color:VT.text, fontFamily:VT.body, fontWeight:500}}>{r.v}</span>
        </div>
      )}
    </Panel>}
    {(loading || error) && <div style={{marginTop:12, fontSize:12, color:error?'#F06571':VT.textMuted}}>{loading ? "Loading client assets..." : error}</div>}
  </div>;
}

// ── END CARD POOL ─────────────────────────────────────────────
function EndCardPool({ nav, clientSlug }) {
  const client = CLIENTS.find(c=>c.slug===clientSlug) || CLIENTS[0];
  const cards = END_CARDS[client.slug] || [];
  return <div style={{padding:'20px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{display:'flex', alignItems:'center', gap:14, marginBottom:20}}>
      <Btn variant="subtle" onClick={()=>nav('assets', clientSlug)}><IC.chev width={16} height={16} style={{transform:'rotate(180deg)'}}/> Back</Btn>
      <div style={{width:1, height:24, background:VT.line}}/>
      <Avatar client={client} size={38}/>
      <div>
        <div style={{fontFamily:VT.display, fontSize:22, fontWeight:600, color:VT.text, letterSpacing:-0.3}}>End card pool</div>
        <div style={{fontSize:12, color:VT.textDim, marginTop:2}}>{client.name} · {cards.length} cards · rotates with each video</div>
      </div>
      <div style={{marginLeft:'auto'}}>
        <Btn variant="primary" icon="plus">New end card</Btn>
      </div>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:14}}>
      {cards.map(c =>
        <Panel key={c.id} pad={0} style={{overflow:'hidden'}}>
          {/* End card preview (3s) */}
          <div style={{aspectRatio:'9/16', background: c.bg, position:'relative', overflow:'hidden', borderBottom:`1px solid ${VT.line}`}}>
            {c.layout==='centered' && <div style={{position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:8}}>
              <div style={{width:50, height:50, borderRadius:10, background: c.accent, opacity:.9}}/>
              <div style={{fontFamily:VT.display, fontWeight:700, fontSize:14, color:'#fff', letterSpacing:1.5, textAlign:'center'}}>{client.company.toUpperCase().slice(0,18)}</div>
              <div style={{width:36, height:1, background: c.accent}}/>
              <div style={{fontSize:10, color: c.accent, letterSpacing:1.5, textTransform:'uppercase'}}>Call today</div>
            </div>}
            {c.layout==='bar_cta' && <>
              <div style={{position:'absolute', inset:0, background:'radial-gradient(circle at 50% 30%, rgba(255,255,255,0.08), transparent 60%)'}}/>
              <div style={{position:'absolute', left:14, right:14, top:'35%', fontFamily:VT.display, fontSize:20, color:'#fff', fontWeight:700, textAlign:'center', lineHeight:1.2}}>Closing<br/>made easy.</div>
              <div style={{position:'absolute', left:14, right:14, bottom:16, padding:'10px 14px', background: c.accent, borderRadius:6, fontSize:12, fontWeight:700, color:'#0A0A0A', textAlign:'center'}}>BOOK A CALL</div>
            </>}
            {c.layout==='split_hero' && <>
              <div style={{position:'absolute', inset:0, background:`linear-gradient(180deg, ${c.bg}, ${c.accent}30)`}}/>
              <div style={{position:'absolute', top:20, left:14, right:14, fontFamily:VT.display, fontSize:15, color:'#fff', fontWeight:700}}>{client.company.split(' ')[0]}</div>
              <div style={{position:'absolute', bottom:40, left:14, right:14, fontSize:10, color:'rgba(255,255,255,0.7)'}}>virtualtwins.ai</div>
              <div style={{position:'absolute', bottom:16, left:14, width:30, height:1.5, background: c.accent}}/>
            </>}
            {c.layout==='fullscreen_mark' && <div style={{position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center'}}>
              <div style={{fontFamily:VT.display, fontSize:48, fontWeight:900, color: c.accent, opacity:.9}}>{client.initials}</div>
            </div>}

            <div style={{position:'absolute', top:8, right:8}}><Pill tone="gold" small>3s</Pill></div>
          </div>

          <div style={{padding:14}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:6}}>
              <div style={{fontSize:13, fontWeight:600, color:VT.text}}>{c.name}</div>
              <IC.dots width={14} height={14} style={{color:VT.textMuted, cursor:'pointer'}}/>
            </div>
            <div style={{fontSize:10.5, color:VT.textMuted, textTransform:'capitalize', marginBottom:10}}>{c.layout.replace('_',' ')} · {c.motion}</div>
            <div style={{display:'flex', gap:8, fontSize:10.5, color:VT.textDim}}>
              <span>Used {c.usage}×</span>
              <span style={{color:VT.textMuted}}>·</span>
              <span>Last {c.lastUsed}</span>
            </div>
          </div>
        </Panel>
      )}
      {/* New */}
      <Panel pad={14} style={{border:`1px dashed ${VT.lineHi}`, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:10, minHeight:300, cursor:'pointer'}}>
        <div style={{width:50, height:50, borderRadius:25, background:'rgba(232,184,96,0.1)', display:'flex', alignItems:'center', justifyContent:'center'}}>
          <IC.plus width={20} height={20} style={{color:'#E8B860'}}/>
        </div>
        <div style={{fontSize:13, fontWeight:600, color:VT.text}}>Design new end card</div>
        <div style={{fontSize:11, color:VT.textMuted, textAlign:'center', maxWidth:180, lineHeight:1.4}}>Pick layout, set copy, uses brand colors from kit</div>
      </Panel>
    </div>
  </div>;
}

// ── HISTORY ─────────────────────────────────────────────
function History({ nav, jobs = [], clients = [], loading = false }) {
  const [statusFilter, setStatusFilter] = useStateR('all');
  const rows = statusFilter==='all' ? jobs : jobs.filter(j=>j.status===statusFilter);

  return <div style={{padding:'24px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between', marginBottom:20}}>
      <div>
        <div style={{fontSize:11, color:VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, marginBottom:4}}>History</div>
        <div style={{fontFamily:VT.display, fontSize:26, fontWeight:600, color:VT.text, letterSpacing:-0.3}}>All video jobs</div>
      </div>
      <div style={{display:'flex', gap:8}}>
        {['all','awaiting_approval','rendering','done','failed','queued'].map(s =>
          <button key={s} onClick={()=>setStatusFilter(s)} style={{
            padding:'6px 12px', borderRadius:6, fontSize:11, fontWeight:600,
            border:`1px solid ${statusFilter===s ? 'rgba(155,92,246,0.4)' : VT.line}`,
            background: statusFilter===s ? 'rgba(155,92,246,0.1)' : 'transparent',
            color: statusFilter===s ? '#C9A8FA' : VT.textDim,
            cursor:'pointer', textTransform:'capitalize', letterSpacing:.3,
          }}>{s.replace('_',' ')}</button>
        )}
      </div>
    </div>

    <Panel pad={0}>
      <div style={{display:'grid', gridTemplateColumns:'70px 1fr 1fr 1fr 90px 90px 80px 120px 40px', alignItems:'center', gap:14, padding:'12px 20px', borderBottom:`1px solid ${VT.line}`, fontSize:10, color:VT.textMuted, letterSpacing:1, textTransform:'uppercase', fontWeight:600}}>
        <div></div>
        <div>Job · Client</div>
        <div>Template</div>
        <div>Prompt</div>
        <div>Clips</div>
        <div>Cost</div>
        <div>Created</div>
        <div>Status</div>
        <div></div>
      </div>
      {rows.map(j => {
        const c = clients.find(cl=>cl.slug===j.client) || { name: j.client, initials: "??", color: "#9B5CF6" };
        const isDelivered = j.status === "done" || j.status === "delivered" || j.status === "awaiting_assembly" || j.stage === "assembly_review";
        return <div key={j.id} onClick={()=>nav(isDelivered ? 'assembly' : 'clip-approve', j.id)} style={{
          display:'grid', gridTemplateColumns:'70px 1fr 1fr 1fr 90px 90px 80px 120px 40px',
          alignItems:'center', gap:14, padding:'14px 20px',
          borderBottom:`1px solid ${VT.line}`,
          cursor: 'pointer',
        }}
        onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.02)'}
        onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
          <div style={{width:54, height:72, borderRadius:6, background: `linear-gradient(160deg, ${j.thumb}40, ${j.thumb}10)`, border:`1px solid ${j.thumb}30`, display:'flex', alignItems:'center', justifyContent:'center'}}>
            <IC.film width={16} height={16} style={{color:j.thumb}}/>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:10}}>
            <Avatar client={c} size={28}/>
            <div>
              <div style={{fontSize:12.5, fontWeight:600, color:VT.text}}>{c.name}</div>
              <div style={{fontSize:10.5, color:VT.textMuted, fontFamily:VT.mono}}>{j.id}</div>
            </div>
          </div>
          <div>
            <div style={{fontSize:12, color:VT.text}}>{j.template}</div>
            <div style={{fontSize:10.5, color:VT.textMuted, marginTop:2}}>{j.format}</div>
          </div>
          <div style={{fontSize:11.5, color:VT.textDim, lineHeight:1.4, maxHeight:36, overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical'}}>{j.prompt}</div>
          <div style={{fontSize:11.5, fontFamily:VT.mono, color:VT.text}}>
            {j.clipsDone}/{j.clipsTotal}
            {j.status==='rendering' && <div style={{height:3, background:'rgba(255,255,255,0.06)', borderRadius:2, marginTop:5}}>
              <div style={{width: `${(j.clipsDone/j.clipsTotal)*100}%`, height:'100%', background:VT.gradBrand, borderRadius:2}}/>
            </div>}
          </div>
          <div style={{fontSize:11.5, fontFamily:VT.mono, color:VT.text}}>
            ${j.cost.toFixed(2)}
            {j.costProjected>j.cost && <div style={{fontSize:10, color:VT.textMuted}}>/ ${j.costProjected.toFixed(2)}</div>}
          </div>
          <div style={{fontSize:11, color:VT.textDim}}>{j.createdAt}</div>
          <div>
            <StatusBadgeForJob status={j.status}/>
            {j.failReason && <div style={{fontSize:10, color:'#F06571', marginTop:3, maxWidth:120}}>{j.failReason.slice(0,40)}…</div>}
          </div>
          <IC.chev width={14} height={14} style={{color:VT.textMuted}}/>
        </div>;
      })}
      {rows.length===0 && <div style={{padding:'16px 20px', color:VT.textMuted, fontSize:12}}>{loading ? 'Loading jobs...' : 'No jobs yet.'}</div>}
    </Panel>
  </div>;
}

// ── COST DASHBOARD ─────────────────────────────────────────────
function CostView({ nav }) {
  const total = COST_SERIES.reduce((a,b)=>a+b,0);
  const avgPerVideo = total / 25;

  return <div style={{padding:'24px 28px', maxWidth:1480, margin:'0 auto'}}>
    <div style={{marginBottom:20}}>
      <div style={{fontSize:11, color:VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, marginBottom:4}}>Cost · 30-day rolling</div>
      <div style={{fontFamily:VT.display, fontSize:26, fontWeight:600, color:VT.text, letterSpacing:-0.3}}>Spend control</div>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:14, marginBottom:20}}>
      <KPICard label="Total spend (30d)" value={`$${total.toFixed(2)}`} delta="-18.2%" accent="#9B5CF6" sub="vs prior 30d"/>
      <KPICard label="Avg / video" value={`$${avgPerVideo.toFixed(2)}`} delta="-$0.42" accent="#E8B860" sub="goal $6.00"/>
      <KPICard label="Rejected spend" value="$12.18" delta="2 jobs" accent="#F06571" sub="approval gate saved $18"/>
      <KPICard label="Margin / client / mo" value="$54.06" delta="+$8" accent="#4FD68A" sub="at $75 MRR / client"/>
    </div>

    <div style={{display:'grid', gridTemplateColumns:'1fr 360px', gap:16}}>
      <Panel pad={20}>
        <SectionHeader title="Daily spend" eyebrow="Each bar = 1 day · purple = approved, gold = projected"
          action={<div style={{display:'flex', gap:6}}>
            <Pill tone="brand" small>approved</Pill>
            <Pill tone="gold" small>in-flight</Pill>
          </div>}/>
        <div style={{display:'flex', alignItems:'flex-end', gap:4, height:220, padding:'20px 0', borderBottom:`1px solid ${VT.line}`, position:'relative'}}>
          {/* goal line */}
          <div style={{position:'absolute', left:0, right:0, top: `${100 - (6/15)*100}%`, height:1, borderTop:'1px dashed rgba(232,184,96,0.4)', pointerEvents:'none'}}>
            <span style={{position:'absolute', right:0, top:-16, fontSize:10, fontFamily: VT.mono, color:'#E8B860'}}>$6 goal</span>
          </div>
          {COST_SERIES.map((v,i) => {
            const h = (v/15)*100;
            const inflight = i===COST_SERIES.length-1;
            return <div key={i} style={{flex:1, display:'flex', flexDirection:'column', justifyContent:'flex-end', alignItems:'center', gap:4, height:'100%'}}>
              <div style={{
                width:'100%', height: `${h}%`,
                background: v===0 ? 'rgba(255,255,255,0.04)' : inflight ? VT.gradGold : 'linear-gradient(180deg, #B57CF8, #6B3FD4)',
                borderRadius:'3px 3px 0 0', minHeight: v===0?2:4,
                opacity: v===0?0.3:1,
              }}/>
            </div>;
          })}
        </div>
        <div style={{display:'flex', justifyContent:'space-between', fontSize:10, color:VT.textMuted, marginTop:8, fontFamily:VT.mono}}>
          <span>Mar 22</span><span>Mar 29</span><span>Apr 5</span><span>Apr 12</span><span>Today</span>
        </div>
      </Panel>

      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        <Panel pad={16}>
          <SectionHeader title="By client · this month" eyebrow="Top spenders"/>
          {[
            {c:CLIENTS[1], v: 24.24, pct:75},
            {c:CLIENTS[0], v: 18.12, pct:55},
            {c:CLIENTS[2], v: 12.16, pct:37},
            {c:CLIENTS[4], v: 11.84, pct:36},
            {c:CLIENTS[3], v: 3.18,  pct:10},
          ].map(row =>
            <div key={row.c.slug} style={{marginBottom:12}}>
              <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:4}}>
                <Avatar client={row.c} size={22}/>
                <div style={{flex:1, fontSize:12, color:VT.text, fontWeight:500}}>{row.c.name}</div>
                <div style={{fontSize:12, fontFamily:VT.mono, color:VT.text, fontWeight:600}}>${row.v.toFixed(2)}</div>
              </div>
              <div style={{height:3, background:VT.bg4, borderRadius:2, marginLeft:30}}>
                <div style={{width:`${row.pct}%`, height:'100%', background: row.c.color, borderRadius:2}}/>
              </div>
            </div>
          )}
        </Panel>

        <Panel pad={16} style={{background:'linear-gradient(135deg, rgba(155,92,246,0.04), rgba(232,184,96,0.03))', border:`1px solid ${VT.lineBrand}`}}>
          <div style={{fontSize:11, color:'#E8B860', fontWeight:600, letterSpacing:1, textTransform:'uppercase', marginBottom:10, display:'flex', alignItems:'center', gap:6}}>
            <IC.sparkle width={12} height={12}/> Cost optimizer
          </div>
          <div style={{fontSize:12, color:VT.text, lineHeight:1.5, marginBottom:12}}>
            Switching Marco's 30s <b>Neighborhood Spotlight</b> to 20s would save ~<b className="vt-gold-text">$36/mo</b> at current cadence.
          </div>
          <Btn variant="ghost" size="sm" style={{width:'100%', justifyContent:'center'}}>Suggest to client</Btn>
        </Panel>
      </div>
    </div>
  </div>;
}

Object.assign(window, { AssetsVault, EndCardPool, History, CostView });
