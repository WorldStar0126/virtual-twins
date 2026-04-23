// Client roster / dashboard
const { useState: useStateD } = React;

function KPICard({ label, value, delta, accent='#9B5CF6', sub }) {
  return <Panel pad={18} style={{position:'relative', overflow:'hidden'}}>
    <div style={{position:'absolute', top:-30, right:-30, width:120, height:120, borderRadius:'50%',
      background:`radial-gradient(circle, ${accent}22, transparent 70%)`}}/>
    <div style={{fontSize:10, fontWeight:600, color: VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', marginBottom:10}}>{label}</div>
    <div style={{fontFamily: VT.display, fontSize:30, fontWeight:600, color: VT.text, letterSpacing:-0.5, lineHeight:1}}>{value}</div>
    <div style={{marginTop:8, display:'flex', alignItems:'center', gap:8}}>
      {delta && <span style={{fontSize:11, color: delta.startsWith('+')?'#4FD68A':'#F06571', fontFamily: VT.mono, fontWeight:500}}>{delta}</span>}
      {sub && <span style={{fontSize:11, color: VT.textMuted}}>{sub}</span>}
    </div>
  </Panel>;
}

function StatusBadgeForJob({ status }) {
  const m = {
    awaiting_approval: { tone:'warn',    label:'Needs approval' },
    rendering:         { tone:'info',    label:'Rendering' },
    done:              { tone:'success', label:'Delivered' },
    failed:            { tone:'danger',  label:'Failed' },
    queued:            { tone:'neutral', label:'Queued' },
  }[status];
  return <Pill tone={m.tone}>{m.label}</Pill>;
}

function ClientRow({ client, onClick, active }) {
  return <div onClick={onClick} style={{
    display:'grid',
    gridTemplateColumns:'auto 1.4fr 1.1fr 1fr 1fr 1fr auto',
    alignItems:'center', gap:14,
    padding:'12px 16px',
    borderRadius: 10,
    cursor:'pointer',
    background: active ? 'rgba(155,92,246,0.08)' : 'transparent',
    border: `1px solid ${active ? 'rgba(155,92,246,0.25)' : 'transparent'}`,
    transition:'background .12s',
  }}
  onMouseEnter={e=>{ if(!active) e.currentTarget.style.background='rgba(255,255,255,0.03)'; }}
  onMouseLeave={e=>{ if(!active) e.currentTarget.style.background='transparent'; }}
  >
    <Avatar client={client} size={38}/>
    <div>
      <div style={{fontSize:13.5, color: VT.text, fontWeight:600}}>{client.name}</div>
      <div style={{fontSize:11.5, color: VT.textDim, marginTop:2}}>{client.company}</div>
    </div>
    <div style={{fontSize:12, color: VT.textDim}}>
      <div>{client.market}</div>
      <div style={{fontSize:10.5, color: VT.textMuted, marginTop:2}}>{client.industry}</div>
    </div>
    <div style={{fontSize:12, color: VT.text, fontFamily: VT.mono}}>
      {client.videosThisMonth}/{client.videoQuota}
      <div style={{height:3, background:'rgba(255,255,255,0.06)', borderRadius:2, marginTop:6, width: 60, overflow:'hidden'}}>
        <div style={{width: `${(client.videosThisMonth/client.videoQuota)*100}%`, height:'100%', background: VT.gradBrand}}/>
      </div>
    </div>
    <div style={{fontSize:11.5, color: VT.textDim}}>{client.lastVideo}</div>
    <div>
      <Pill tone={client.status==='Active'?'success': client.status==='Onboarding'?'brand':'info'} small>{client.status}</Pill>
    </div>
    <IC.chev width={16} height={16} style={{color: VT.textMuted}}/>
  </div>;
}

function JobMiniRow({ job, client, onClick }) {
  return <div onClick={onClick} style={{
    display:'flex', gap:12, alignItems:'center',
    padding:'10px 12px', borderRadius:8, cursor:'pointer',
    transition:'background .12s',
  }}
  onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.03)'}
  onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
    <div style={{width:44, height:54, borderRadius:6, overflow:'hidden', flexShrink:0,
      background:`linear-gradient(160deg, ${job.thumb}40, ${job.thumb}10)`,
      border:`1px solid ${job.thumb}30`,
      display:'flex', alignItems:'center', justifyContent:'center',
    }}>
      <IC.film width={16} height={16} style={{color: job.thumb}}/>
    </div>
    <div style={{flex:1, minWidth:0}}>
      <div style={{fontSize:12.5, fontWeight:600, color: VT.text, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{client?.name}</div>
      <div style={{fontSize:11, color: VT.textDim, marginTop:2, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{job.template} · {job.format}</div>
    </div>
    <StatusBadgeForJob status={job.status}/>
  </div>;
}

function Dashboard({ nav, clients = [], jobs = [], loading = false, error = null, connected = false }) {
  const [filter, setFilter] = useStateD('all');
  const filtered = filter==='all' ? clients : clients.filter(c=>c.status==='Active');
  const needsApproval = jobs.filter(j=>j.status==='awaiting_approval');
  const rendering = jobs.filter(j=>j.status==='rendering');
  const failed = jobs.filter(j=>j.status==='failed');

  return <div style={{padding:28, display:'flex', flexDirection:'column', gap:24, maxWidth:1600, margin:'0 auto'}}>
    {/* Header */}
    <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between'}}>
      <div>
        <div style={{fontSize:11, color: VT.textMuted, letterSpacing:1.5, textTransform:'uppercase', fontWeight:600, marginBottom:6}}>Operator Studio</div>
        <div style={{fontFamily: VT.display, fontSize:30, fontWeight:600, color: VT.text, letterSpacing:-0.5}}>Good morning, Adam.</div>
        <div style={{fontSize:13, color: VT.textDim, marginTop:4}}>You have <b style={{color:'#F2C97A'}}>{needsApproval.length} clip{needsApproval.length===1?'':'s'}</b> awaiting approval and <b style={{color:'#7CA7FF'}}>{rendering.length} rendering</b>. {failed.length>0 && <>· <b style={{color:'#F06571'}}>{failed.length} failed</b></>}</div>
        <div style={{fontSize:11, color: error ? '#F06571' : VT.textMuted, marginTop:6}}>
          {loading ? 'Syncing backend...' : connected ? 'Connected to live backend' : (error || 'Using offline data')}
        </div>
      </div>
      <Btn variant="primary" icon="plus" size="lg" onClick={()=>nav('job-new')}>New video job</Btn>
    </div>

    {/* KPIs */}
    <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:14}}>
      <KPICard label="Active clients" value="6" delta="+2 this mo" accent="#9B5CF6" sub="2 onboarding"/>
      <KPICard label="Videos delivered · Apr" value="12" delta="+3 vs Mar" accent="#E8B860" sub="78% approval rate"/>
      <KPICard label="Spend this mo" value="$148.60" delta="-$31.20" accent="#4FD68A" sub="under $250 budget"/>
      <KPICard label="Avg cost / video" value="$5.94" delta="-$0.42" accent="#7CA7FF" sub="goal: $6.00"/>
    </div>

    {/* Two-column: Queue + Client roster */}
    <div style={{display:'grid', gridTemplateColumns:'1fr 380px', gap:16, alignItems:'flex-start'}}>
      {/* Client roster */}
      <Panel pad={18}>
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16}}>
          <SectionHeader title="Client roster" eyebrow="All markets"/>
          <div style={{display:'flex', gap:6}}>
            {['all','active'].map(f =>
              <button key={f} onClick={()=>setFilter(f)} style={{
                padding:'5px 11px', borderRadius:6, fontSize:11, fontWeight:600,
                border:`1px solid ${filter===f ? 'rgba(155,92,246,0.4)' : VT.line}`,
                background: filter===f ? 'rgba(155,92,246,0.12)' : 'transparent',
                color: filter===f ? '#C9A8FA' : VT.textDim,
                cursor:'pointer', textTransform:'uppercase', letterSpacing:.5,
              }}>{f}</button>
            )}
            <div style={{width:1, background: VT.line, margin:'0 4px'}}/>
            <button style={{padding:'5px 10px', borderRadius:6, fontSize:11, border:`1px solid ${VT.line}`, background:'transparent', color: VT.textDim, cursor:'pointer', display:'flex', alignItems:'center', gap:5}}>
              <IC.search width={12} height={12}/> Search
            </button>
          </div>
        </div>
        {/* column headers */}
        <div style={{
          display:'grid', gridTemplateColumns:'auto 1.4fr 1.1fr 1fr 1fr 1fr auto',
          gap:14, padding:'0 16px 8px', fontSize:10,
          color: VT.textMuted, fontWeight:600, letterSpacing:1.2, textTransform:'uppercase',
          borderBottom: `1px solid ${VT.line}`, marginBottom:6,
        }}>
          <div style={{width:38}}></div>
          <div>Client</div>
          <div>Market</div>
          <div>Quota</div>
          <div>Last</div>
          <div>Status</div>
          <div></div>
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:2}}>
          {filtered.map(c => <ClientRow key={c.slug} client={c} onClick={()=>nav('assets', c.slug)}/>)}
          {filtered.length===0 && <div style={{padding:'24px 16px', color:VT.textMuted, fontSize:12}}>No clients found yet.</div>}
        </div>
      </Panel>

      {/* Job queue sidebar */}
      <div style={{display:'flex', flexDirection:'column', gap:14}}>
        <Panel pad={16}>
          <SectionHeader title="Awaiting your approval" eyebrow={`${needsApproval.length} · action needed`}
            action={<span style={{fontSize:11, color:'#F2C97A', fontWeight:600, display:'flex', alignItems:'center', gap:4}}><IC.warn width={12} height={12}/> gated</span>}/>
          <div style={{display:'flex', flexDirection:'column', gap:4}}>
            {needsApproval.map(j => <JobMiniRow key={j.id} job={j} client={clients.find(c=>c.slug===j.client)} onClick={()=>nav('clip-approve', j.id)}/>)}
            {needsApproval.length===0 && <div style={{fontSize:12, color: VT.textMuted, padding:'20px 12px', textAlign:'center'}}>All caught up. ✓</div>}
          </div>
        </Panel>

        <Panel pad={16}>
          <SectionHeader title="Rendering now" eyebrow={`${rendering.length} · live`}/>
          <div style={{display:'flex', flexDirection:'column', gap:4}}>
            {rendering.map(j => <JobMiniRow key={j.id} job={j} client={clients.find(c=>c.slug===j.client)} onClick={()=>nav('history', j.id)}/>)}
          </div>
        </Panel>

        {failed.length>0 && <Panel pad={16} style={{border:`1px solid rgba(240,101,113,0.2)`}}>
          <SectionHeader title="Needs retry" eyebrow={`${failed.length} · failed`}/>
          {failed.map(j => <JobMiniRow key={j.id} job={j} client={clients.find(c=>c.slug===j.client)} onClick={()=>nav('history', j.id)}/>)}
        </Panel>}
      </div>
    </div>
  </div>;
}

window.Dashboard = Dashboard;
