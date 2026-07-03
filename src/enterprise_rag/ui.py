HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Atlas RAG Workspace</title>
  <style>
    :root {
      --navy:#10243e; --navy2:#18395d; --ink:#172536; --muted:#66758a;
      --paper:#f3f6f8; --card:#ffffff; --line:#dce4ea; --teal:#087f8c;
      --teal2:#0ba7a5; --amber:#b76818; --danger:#a13d3d; --soft:#eaf5f5;
      --shadow:0 20px 60px rgba(19,44,70,.10);
    }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--paper);
      font-family:Inter,Segoe UI,system-ui,sans-serif; }
    button,input,textarea,select { font:inherit; }
    button { cursor:pointer; }
    .shell { min-height:100vh; display:grid; grid-template-columns:300px 1fr; }
    aside { background:linear-gradient(180deg,var(--navy),#0b1b2d); color:white;
      padding:28px 22px; position:sticky; top:0; height:100vh; overflow:auto; }
    .brand { display:flex; align-items:center; gap:12px; margin-bottom:34px; }
    .mark { width:42px; height:42px; display:grid; place-items:center; border-radius:13px;
      background:linear-gradient(135deg,var(--teal2),#76d3c8); font-weight:900; color:var(--navy); }
    .brand strong { display:block; font-size:1.08rem; }
    .brand small { color:#aab9ca; }
    .nav-title { color:#8398ad; text-transform:uppercase; letter-spacing:.14em;
      font-size:.7rem; font-weight:800; margin:24px 8px 10px; }
    .nav-button { width:100%; border:0; text-align:left; padding:12px 14px; border-radius:11px;
      background:transparent; color:#c7d3df; margin:3px 0; }
    .nav-button.active,.nav-button:hover { background:#ffffff12; color:white; }
    .side-stat { border:1px solid #ffffff1f; background:#ffffff0a; border-radius:14px;
      padding:15px; margin-top:20px; }
    .side-stat b { display:block; font-size:1.5rem; }
    .side-stat span { color:#9fb0c1; font-size:.82rem; }
    main { min-width:0; }
    .topbar { height:76px; display:flex; align-items:center; justify-content:space-between;
      padding:0 34px; background:#ffffffcc; backdrop-filter:blur(14px);
      border-bottom:1px solid var(--line); position:sticky; top:0; z-index:5; }
    .topbar h1 { font-size:1.15rem; margin:0; }
    .health { display:flex; gap:8px; align-items:center; color:var(--muted); font-size:.88rem; }
    .dot { width:9px; height:9px; border-radius:50%; background:#37b879;
      box-shadow:0 0 0 5px #37b87919; }
    .content { width:min(1180px,calc(100% - 48px)); margin:30px auto 60px; }
    .view { display:none; }
    .view.active { display:block; }
    .hero { display:flex; justify-content:space-between; gap:24px; align-items:end; margin-bottom:24px; }
    .eyebrow { color:var(--teal); font-size:.74rem; text-transform:uppercase;
      letter-spacing:.16em; font-weight:850; }
    h2 { margin:7px 0 5px; font-size:clamp(1.7rem,3vw,2.6rem); letter-spacing:-.035em; }
    .sub { color:var(--muted); margin:0; line-height:1.6; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:18px;
      padding:22px; box-shadow:var(--shadow); }
    .card h3 { margin:0 0 7px; font-size:1.05rem; }
    .drop { border:2px dashed #b9c9d4; border-radius:15px; min-height:190px;
      display:grid; place-items:center; text-align:center; padding:24px; transition:.2s; }
    .drop.drag { border-color:var(--teal); background:var(--soft); }
    .drop-icon { width:52px; height:52px; display:grid; place-items:center; margin:0 auto 12px;
      border-radius:16px; background:var(--soft); color:var(--teal); font-size:1.5rem; }
    input[type=file] { display:none; }
    .button { border:0; background:linear-gradient(135deg,var(--teal),var(--teal2)); color:white;
      border-radius:10px; padding:11px 17px; font-weight:750; }
    .button.secondary { color:var(--ink); background:#edf2f5; }
    .button:disabled { opacity:.55; cursor:wait; }
    .field { width:100%; padding:12px 13px; border:1px solid var(--line); border-radius:10px;
      background:white; color:var(--ink); outline:none; }
    .field:focus { border-color:var(--teal); box-shadow:0 0 0 3px #0ba7a51c; }
    .row { display:flex; gap:10px; align-items:center; margin-top:12px; }
    .row .field { flex:1; }
    .options { display:flex; gap:18px; flex-wrap:wrap; color:var(--muted);
      font-size:.86rem; margin-top:14px; }
    .progress-card { margin-top:20px; display:none; }
    .progress-card.active { display:block; }
    .progress-head { display:flex; justify-content:space-between; gap:15px; margin-bottom:10px; }
    .track { height:9px; background:#e7edf1; border-radius:99px; overflow:hidden; }
    .bar { height:100%; width:0; background:linear-gradient(90deg,var(--teal),#4bc4b7);
      border-radius:99px; transition:width .3s; }
    .docs { display:grid; gap:12px; margin-top:20px; }
    .doc { display:grid; grid-template-columns:48px 1fr auto; gap:14px; align-items:center;
      border:1px solid var(--line); background:white; border-radius:14px; padding:14px; }
    .doc-icon { width:48px; height:48px; display:grid; place-items:center; border-radius:12px;
      background:#eef3f8; color:var(--navy2); font-weight:900; }
    .doc-name { font-weight:750; overflow-wrap:anywhere; }
    .doc-meta { color:var(--muted); font-size:.83rem; margin-top:4px; }
    .badge { padding:6px 9px; border-radius:99px; background:#e8f7f0; color:#24714f;
      font-size:.75rem; font-weight:800; }
    .button.danger { color:var(--danger); background:#fff1f1; }
    .mini-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin-top:10px; }
    .mini-stat { border:1px solid var(--line); border-radius:11px; background:#fbfdfe; padding:9px; }
    .mini-stat b { display:block; color:var(--navy2); }
    .mini-stat span { color:var(--muted); font-size:.72rem; }
    .pipeline { display:grid; gap:9px; margin-top:14px; }
    .pipeline-step { border:1px solid var(--line); border-radius:13px; background:#fbfdfe; padding:12px; position:relative; }
    .pipeline-step:before { content:""; position:absolute; left:-1px; top:12px; bottom:12px; width:4px; background:var(--teal); border-radius:99px; }
    .pipeline-title { display:flex; justify-content:space-between; gap:10px; font-weight:850; padding-left:8px; }
    .pipeline-body { color:var(--muted); font-size:.8rem; line-height:1.45; margin-top:7px; padding-left:8px; overflow-wrap:anywhere; }
    .provider-grid { display:grid; gap:10px; margin-top:14px; }
    .provider-card { border:1px solid var(--line); border-radius:13px; background:#fbfdfe; padding:12px; }
    .provider-head { display:flex; justify-content:space-between; gap:10px; align-items:center; font-weight:850; }
    .provider-score { font-size:1.2rem; color:var(--navy2); font-weight:900; }
    .meter { height:7px; border-radius:99px; overflow:hidden; background:#e7edf1; margin:9px 0; }
    .meter > span { display:block; height:100%; background:linear-gradient(90deg,var(--teal),var(--teal2)); }
    .flow-board { display:grid; gap:11px; }
    .flow-node { border:1px solid var(--line); border-radius:15px; background:white; padding:15px; box-shadow:var(--shadow); }
    .flow-node h3 { margin:0 0 8px; display:flex; justify-content:space-between; gap:10px; }
    .flow-methods { display:flex; flex-wrap:wrap; gap:7px; }
    .chat-layout { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:20px; }
    .chat { min-height:650px; display:flex; flex-direction:column; padding:0; overflow:hidden; }
    .chat-head { padding:18px 22px; border-bottom:1px solid var(--line);
      display:flex; justify-content:space-between; align-items:center; }
    .messages { flex:1; padding:24px; overflow:auto; max-height:570px; }
    .welcome { text-align:center; max-width:590px; margin:75px auto 20px; }
    .welcome-mark { width:68px; height:68px; display:grid; place-items:center; margin:auto;
      border-radius:22px; color:white; background:linear-gradient(135deg,var(--navy2),var(--teal)); font-size:1.8rem; }
    .suggestions { display:flex; justify-content:center; gap:8px; flex-wrap:wrap; margin-top:20px; }
    .suggestion { border:1px solid var(--line); background:white; border-radius:99px;
      padding:8px 12px; color:var(--navy2); font-size:.82rem; }
    .message { margin-bottom:20px; }
    .message.user { margin-left:12%; }
    .message.assistant { margin-right:5%; }
    .bubble { padding:15px 17px; border-radius:16px; line-height:1.62; white-space:pre-wrap; }
    .user .bubble { background:var(--navy2); color:white; border-bottom-right-radius:4px; }
    .assistant .bubble { background:#f0f5f7; border:1px solid #e2eaee; border-bottom-left-radius:4px; }
    .message-meta { color:var(--muted); font-size:.76rem; margin:6px 4px; }
    .composer { border-top:1px solid var(--line); padding:15px; display:flex; gap:10px; }
    .composer textarea { min-height:48px; max-height:140px; resize:vertical; }
    .send { width:48px; border:0; border-radius:12px; color:white;
      background:linear-gradient(135deg,var(--teal),var(--teal2)); font-size:1.1rem; }
    .evidence-list { display:grid; gap:10px; margin-top:15px; }
    details { border:1px solid var(--line); border-radius:11px; background:white; padding:11px; }
    summary { cursor:pointer; font-weight:720; font-size:.86rem; }
    .passage { color:#425367; line-height:1.55; font-size:.86rem; white-space:pre-wrap;
      max-height:260px; overflow:auto; margin-top:10px; }
    .visual-snapshot { margin-top:12px; border:1px solid var(--line); border-radius:12px;
      overflow:hidden; background:#f8fbfc; }
    .visual-snapshot img { display:block; width:100%; max-height:420px; object-fit:contain;
      background:white; }
    .visual-caption { padding:9px 10px; color:var(--muted); font-size:.76rem;
      border-top:1px solid var(--line); }
    .safety { border-left:4px solid var(--amber); background:#fff8ed; padding:13px 14px;
      border-radius:0 10px 10px 0; color:#6c4a20; font-size:.84rem; line-height:1.5; }
    .settings-line { display:flex; justify-content:space-between; gap:12px; padding:12px 0;
      border-bottom:1px solid var(--line); color:var(--muted); font-size:.88rem; }
    .settings-line b { color:var(--ink); }
    .memory-pill { color:#24665f; background:#e8f7f3; border-radius:99px;
      padding:5px 9px; font-size:.75rem; font-weight:800; }
    .empty { color:var(--muted); text-align:center; padding:30px; border:1px dashed var(--line);
      border-radius:14px; }
    .metric-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:14px; }
    .metric { border:1px solid var(--line); border-radius:12px; padding:11px; background:#fbfdfe; }
    .metric b { display:block; font-size:1.15rem; color:var(--navy2); }
    .metric span { color:var(--muted); font-size:.76rem; }
    .method-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
    .method-card { border:1px solid var(--line); border-radius:14px; padding:15px; background:white; }
    .method-card h3 { margin:0 0 10px; }
    .method { border-top:1px solid var(--line); padding:10px 0; }
    .method:first-of-type { border-top:0; }
    .method-name { display:flex; justify-content:space-between; gap:10px; font-weight:800; }
    .status-pill { border-radius:99px; padding:3px 8px; font-size:.68rem; text-transform:uppercase; background:#edf2f5; color:#486174; }
    .status-pill.active,.status-pill.active-lite,.status-pill.active-proxy { background:#e8f7f0; color:#24714f; }
    .status-pill.completed { background:#e8f7f0; color:#24714f; }
    .status-pill.planned,.status-pill.gold-required { background:#fff3dd; color:#8a5a12; }
    .status-pill.available-not-configured,.status-pill.not-run,.status-pill.provider-ready,.status-pill.ready-not-run,.status-pill.native-ready { background:#edf2f5; color:#486174; }
    .status-pill.completed-proxy { background:#e9f7ff; color:#1c678a; }
    .status-pill.native-blocked { background:#fff3dd; color:#8a5a12; }
    .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-bottom:18px; }
    .summary-item { border:1px solid var(--line); border-radius:13px; background:white; padding:14px; }
    .summary-item small { color:var(--muted); text-transform:uppercase; letter-spacing:.1em; font-weight:800; }
    .summary-item div { margin-top:6px; font-weight:750; }
    @media(max-width:900px) {
      .shell { grid-template-columns:1fr; } aside { height:auto; position:static; padding:18px; }
      .brand { margin:0; } .nav-title,.side-stat { display:none; }
      aside nav { display:flex; margin-top:12px; } .nav-button { text-align:center; }
      .grid,.chat-layout { grid-template-columns:1fr; } .topbar { padding:0 20px; }
      .content { width:min(94%,1180px); } .evidence-card { order:2; }
    }
  </style>
</head>
<body>
<div class="shell">
  <aside>
    <div class="brand"><div class="mark">A</div><div><strong>Atlas RAG</strong><small>Document intelligence workspace</small></div></div>
    <div class="nav-title">Workspace</div>
    <nav>
      <button class="nav-button active" data-view="sources">Source library</button>
      <button class="nav-button" data-view="chat">Ask documents</button>
      <button class="nav-button" data-view="metrics">RAG metrics</button>
    </nav>
    <div class="side-stat"><b id="sideDocs">0</b><span>indexed documents</span></div>
    <div class="side-stat"><b id="sideChunks">0</b><span>searchable chunks</span></div>
  </aside>
  <main>
    <div class="topbar"><h1 id="viewTitle">Source library</h1><div class="health"><span class="dot"></span><span id="health">Connecting...</span></div></div>
    <div class="content">
      <section class="view active" id="sources">
        <div class="hero"><div><div class="eyebrow">Knowledge ingestion</div><h2>Build your evidence library</h2>
          <p class="sub">Upload a PDF or point to a local file. Atlas extracts, chunks, and indexes it in the background.</p></div></div>
        <div class="grid">
          <div class="card">
            <h3>Upload documents</h3><p class="sub">PDF files are copied into the project data directory.</p>
            <div class="drop" id="drop">
              <div><div class="drop-icon">+</div><strong>Drop a PDF here</strong><p class="sub">or choose a file from this computer</p>
                <button class="button secondary" id="choose">Choose PDF</button><input id="file" type="file" accept=".pdf,application/pdf"></div>
            </div>
          </div>
          <div class="card">
            <h3>Index a local file or folder</h3><p class="sub">Enter one PDF path, or a folder containing multiple PDFs.</p>
            <div class="row"><input class="field" id="path" value="C:\Users\yadav\Desktop\CURRENT Medical Diagnosis _ Treatment 2026.pdf">
              <button class="button" id="indexPath">Index</button></div>
            <div class="options">
              <label><input type="radio" name="mode" value="replace" checked> Replace current index</label>
              <label><input type="radio" name="mode" value="append"> Add to library</label>
              <label>Test pages <input class="field" id="maxPages" type="number" min="1" placeholder="All" style="width:82px;padding:6px"></label>
            </div>
            <div class="safety" style="margin-top:22px">Large books can take several minutes. Start with 20-50 pages to test retrieval, then index the complete document.</div>
          </div>
        </div>
        <div class="card progress-card" id="progressCard">
          <div class="progress-head"><div><strong id="progressFile">Preparing document</strong><div class="sub" id="progressMessage">Queued</div></div><b id="progressPercent">0%</b></div>
          <div class="track"><div class="bar" id="bar"></div></div>
        </div>
        <div class="hero" style="margin-top:32px;margin-bottom:12px"><div><div class="eyebrow">Current index</div><h2 style="font-size:1.7rem">Indexed documents</h2></div></div>
        <div class="docs" id="documents"><div class="empty">No documents indexed yet.</div></div>
      </section>

      <section class="view" id="chat">
        <div class="hero"><div><div class="eyebrow">Grounded Q&A</div><h2>Ask your document library</h2>
          <p class="sub">Answers are generated from retrieved passages and include page-level evidence.</p></div></div>
        <div class="chat-layout">
          <div class="card chat">
            <div class="chat-head"><div><strong>Research conversation</strong> <span class="memory-pill">Context memory on</span></div><button class="button secondary" id="clearChat">Clear</button></div>
            <div class="messages" id="messages">
              <div class="welcome" id="welcome"><div class="welcome-mark">?</div><h3>What do you want to investigate?</h3>
                <p class="sub">Ask for summaries, comparisons, definitions, or passages. Verify medical information with a qualified professional.</p>
                <div class="suggestions">
                  <button class="suggestion">What are the diagnostic criteria for diabetes?</button>
                  <button class="suggestion">Summarize the treatment of hypertension.</button>
                  <button class="suggestion">What are the red flags for headache?</button>
                </div>
              </div>
            </div>
            <div class="composer"><textarea class="field" id="question" placeholder="Ask a question about the indexed documents..."></textarea><button class="send" id="send">&#8593;</button></div>
          </div>
          <div>
            <div class="card evidence-card">
              <div class="eyebrow">Evidence panel</div><h3 style="margin-top:8px">Retrieved sources</h3>
              <div id="evidence" class="evidence-list"><div class="empty">Citations will appear after a question.</div></div>
            </div>
            <div class="card" style="margin-top:16px">
              <div class="eyebrow">Pipeline trace</div><h3 style="margin-top:8px">RAG process</h3>
              <div id="pipelineTrace" class="pipeline"><div class="empty">Pipeline trace will appear after a question.</div></div>
            </div>
            <div class="card" style="margin-top:16px">
              <div class="eyebrow">Answer quality</div><h3 style="margin-top:8px">Live measurements</h3>
              <div id="metrics" class="metric-grid"><div class="empty" style="grid-column:1/-1">Metrics will appear after a question.</div></div>
              <div id="providerResults" class="evidence-list" style="margin-top:14px"></div>
            </div>
            <div class="card" style="margin-top:16px">
              <div class="safety"><strong>Medical safety</strong><br>This research tool summarizes indexed material. It does not diagnose conditions, prescribe treatment, or replace professional care. Seek urgent help for emergencies.</div>
              <div class="settings-line"><span>Answer provider</span><b><select id="generationProvider"></select></b></div>
              <div class="settings-line"><span>Model</span><b><select id="generationModel"></select></b></div>
              <div class="settings-line"><span>Use LLM</span><b><input id="generate" type="checkbox" checked> enabled</b></div>
              <div class="doc-meta" id="generationHelp" style="margin-top:10px">Loading generation providers...</div>
              <div class="settings-line"><span>Native evaluators</span><b><input id="nativeEval" type="checkbox" checked> run</b></div>
              <div class="settings-line"><span>Evidence passages</span><b><select id="topk"><option>3</option><option selected>5</option><option>8</option><option>12</option></select></b></div>
              <div class="settings-line"><span>Retrieval</span><b id="retrievalMode">Loading</b></div>
            </div>
          </div>
        </div>
      </section>

      <section class="view" id="metrics">
        <div class="hero"><div><div class="eyebrow">RAG architecture</div><h2>Methods and measurements</h2>
          <p class="sub">This page separates what is active today from what is available or planned, and explains which metrics need a labeled gold set.</p></div></div>
        <div class="summary-grid" id="architectureSummary"></div>
        <div class="card" style="margin-bottom:18px">
          <div class="eyebrow">Enterprise flow</div><h3 style="margin-top:8px">RAG pipeline architecture</h3>
          <div class="flow-board" id="architectureFlow"><div class="empty">Loading pipeline flow...</div></div>
        </div>
        <div class="card" style="margin-bottom:18px">
          <div class="eyebrow">Evaluation providers</div><h3 style="margin-top:8px">RAGAS, DeepEval, TruLens, LangSmith</h3>
          <div class="method-grid" id="evaluatorProviders"><div class="empty">Loading evaluator providers...</div></div>
        </div>
        <div class="method-grid" id="architectureMethods"><div class="empty">Loading architecture report...</div></div>
      </section>
    </div>
  </main>
</div>
<script>
const $=s=>document.querySelector(s), esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let activeJob=null,conversationId=sessionStorage.getItem("atlasConversationId"),generationProviders=[];
async function responseData(response){
  const text=await response.text();
  if(!text)return {};
  try{return JSON.parse(text);}catch{
    throw new Error(response.ok?"The server returned an unreadable response.":text.slice(0,240));
  }
}
function selectView(name){
  document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id===name));
  document.querySelectorAll(".nav-button").forEach(x=>x.classList.toggle("active",x.dataset.view===name));
  $("#viewTitle").textContent=name==="chat"?"Ask documents":"Source library";
  if(name==="metrics")$("#viewTitle").textContent="RAG metrics";
}
document.querySelectorAll(".nav-button").forEach(b=>b.onclick=()=>selectView(b.dataset.view));
async function refresh(){
  try{
    const [statusResponse,docsResponse,providerResponse]=await Promise.all([fetch("/api/status"),fetch("/api/documents"),fetch("/api/generation/providers")]);
    const status=await statusResponse.json(),docs=await docsResponse.json(),providers=await providerResponse.json();
    generationProviders=providers;
    $("#health").textContent="API online"; $("#sideDocs").textContent=status.document_count;
    $("#sideChunks").textContent=status.chunk_count; $("#retrievalMode").textContent=status.retrieval_mode;
    $("#documents").innerHTML=docs.length?docs.map(d=>`<div class="doc"><div class="doc-icon">PDF</div><div>
      <div class="doc-name">${esc(d.source_file)}</div><div class="doc-meta">${d.page_count.toLocaleString()} pages | ${d.chunk_count.toLocaleString()} chunks | ${d.ocr_page_count} OCR pages</div>
      <div class="mini-grid">
        <div class="mini-stat"><b>${Math.round(d.chunk_count/Math.max(1,d.page_count))}</b><span>chunks/page</span></div>
        <div class="mini-stat"><b>${d.ocr_page_count}</b><span>OCR routed</span></div>
        <div class="mini-stat"><b>${d.low_quality_page_count}</b><span>low quality</span></div>
      </div>
      <details style="margin-top:10px"><summary>Inspect ingestion</summary>
        <div class="pipeline">
          <div class="pipeline-step"><div class="pipeline-title">Document understanding <span class="status-pill active">active</span></div><div class="pipeline-body">PyMuPDF parsing, OCR routing, page snapshots, extraction quality scoring.</div></div>
          <div class="pipeline-step"><div class="pipeline-title">Chunking <span class="status-pill active">active</span></div><div class="pipeline-body">Section-aware parent-child chunks with semantic boundaries and ${d.chunk_count.toLocaleString()} searchable child chunks.</div></div>
          <div class="pipeline-step"><div class="pipeline-title">Storage <span class="status-pill active">local</span></div><div class="pipeline-body">Pages, chunks, metadata, and document summary are stored in local JSONL index files.</div></div>
        </div>
      </details>
      </div><div class="row" style="margin-top:0;justify-content:flex-end"><span class="badge">Ready</span><button class="button danger remove-doc" data-document-id="${esc(d.document_id)}" data-source-file="${esc(d.source_file)}">Remove</button></div></div>`).join(""):`<div class="empty">No documents indexed yet.</div>`;
    document.querySelectorAll(".remove-doc").forEach(button=>button.onclick=()=>removeDocument(button.dataset.documentId,button.dataset.sourceFile));
    renderGenerationProviders(status.generation_provider);
  }catch{$("#health").textContent="API unavailable";}
}
function renderGenerationProviders(defaultProvider){
  const providerSelect=$("#generationProvider"),modelSelect=$("#generationModel");
  if(!providerSelect||!modelSelect||!generationProviders.length)return;
  providerSelect.innerHTML=generationProviders.map(provider=>`<option value="${esc(provider.provider)}" ${provider.status==="active"?"":"disabled"}>${esc(provider.label)} · ${esc(provider.status)}</option>`).join("");
  const activeProviders=generationProviders.filter(provider=>provider.status==="active");
  providerSelect.value=activeProviders.some(p=>p.provider===defaultProvider)?defaultProvider:(activeProviders[0]||generationProviders[0]).provider;
  function syncModels(){
    const provider=generationProviders.find(item=>item.provider===providerSelect.value)||generationProviders[0];
    const models=provider.models?.length?provider.models:[provider.default_model];
    modelSelect.innerHTML=models.map(model=>`<option value="${esc(model)}">${esc(model)}</option>`).join("");
    modelSelect.value=provider.default_model&&models.includes(provider.default_model)?provider.default_model:models[0];
    $("#generationHelp").textContent=`${provider.best_for} Setup: ${provider.setup}`;
  }
  providerSelect.onchange=syncModels;
  syncModels();
}
async function loadArchitecture(){
  try{
    const [response,evaluatorResponse]=await Promise.all([fetch("/api/architecture"),fetch("/api/evaluators")]);
    const data=await responseData(response),evaluators=await responseData(evaluatorResponse);
    $("#architectureSummary").innerHTML=Object.entries(data.active_summary).map(([key,value])=>`
      <div class="summary-item"><small>${esc(key)}</small><div>${esc(value)}</div></div>`).join("");
    $("#architectureFlow").innerHTML=data.layers.map((layer,index)=>`<div class="flow-node">
      <h3><span>${index+1}. ${esc(layer.layer.replace(/^\d+\.\s*/,""))}</span><span class="status-pill active">pipeline</span></h3>
      <div class="flow-methods">${layer.methods.map(method=>`<span class="status-pill ${esc(method.status)}">${esc(method.name)}: ${esc(method.status)}</span>`).join("")}</div>
    </div>`).join("");
    $("#evaluatorProviders").innerHTML=evaluators.map(provider=>`<div class="method-card">
      <div class="method-name">${esc(provider.provider)} <span class="status-pill ${esc(provider.status)}">${esc(provider.status)}</span></div>
      <div class="doc-meta" style="margin-top:9px"><b>Best for:</b> ${esc(provider.best_for)}</div>
      <div class="doc-meta" style="margin-top:7px"><b>Setup:</b> ${esc(provider.required_setup)}</div>
    </div>`).join("");
    $("#architectureMethods").innerHTML=data.layers.map(layer=>`<div class="method-card">
      <h3>${esc(layer.layer)}</h3>
      ${layer.methods.map(method=>`<div class="method"><div class="method-name">${esc(method.name)}
      <span class="status-pill ${esc(method.status)}">${esc(method.status)}</span></div>
      <div class="doc-meta">${esc(method.notes)}</div></div>`).join("")}
    </div>`).join("");
  }catch(e){$("#architectureMethods").innerHTML=`<div class="empty">Could not load architecture report: ${esc(e.message)}</div>`;}
}
function options(){
  return {replace_index:document.querySelector('input[name="mode"]:checked').value==="replace",
    max_pages:$("#maxPages").value?Number($("#maxPages").value):null};
}
async function startPath(){
  const path=$("#path").value.trim(); if(!path)return;
  $("#indexPath").disabled=true;
  try{
    const response=await fetch("/api/index/path",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path,...options()})});
    const data=await responseData(response); if(!response.ok)throw new Error(data.detail||"Could not start indexing");
    watchJob(data);
  }catch(e){alert(e.message);$("#indexPath").disabled=false;}
}
async function startUpload(file){
  if(!file)return; const form=new FormData(),opts=options();
  form.append("file",file); form.append("replace_index",opts.replace_index);
  if(opts.max_pages)form.append("max_pages",opts.max_pages);
  try{
    const response=await fetch("/api/index/upload",{method:"POST",body:form}),data=await responseData(response);
    if(!response.ok)throw new Error(data.detail||"Upload failed"); watchJob(data);
  }catch(e){alert(e.message);}
}
async function removeDocument(documentId,sourceFile){
  if(!documentId)return;
  const confirmed=confirm(`Remove "${sourceFile}" from the index?\n\nThis only removes searchable pages and chunks. It will not delete the original PDF file.`);
  if(!confirmed)return;
  try{
    const response=await fetch(`/api/documents/${encodeURIComponent(documentId)}`,{method:"DELETE"});
    const data=await responseData(response);
    if(!response.ok)throw new Error(data.detail||"Could not remove document");
    if(conversationId)await fetch(`/api/conversations/${conversationId}`,{method:"DELETE"}).catch(()=>{});
    conversationId=null;sessionStorage.removeItem("atlasConversationId");
    $("#messages").innerHTML=`<div class="welcome" id="welcome"><div class="welcome-mark">?</div><h3>Document removed</h3><p class="sub">Start a new research question against the updated index.</p></div>`;
    $("#evidence").innerHTML=`<div class="empty">Citations will appear after a question.</div>`;
    $("#metrics").innerHTML=`<div class="empty" style="grid-column:1/-1">Metrics will appear after a question.</div>`;
    $("#providerResults").innerHTML="";
    await refresh();
  }catch(e){alert(e.message);}
}
function watchJob(job){
  activeJob=job.job_id; $("#progressCard").classList.add("active"); $("#progressFile").textContent=job.source_file;
  $("#indexPath").disabled=true; pollJob();
}
async function pollJob(){
  if(!activeJob)return;
  const response=await fetch(`/api/jobs/${activeJob}`),job=await responseData(response);
  const pct=job.total_pages?Math.round(job.current_page/job.total_pages*100):0;
  $("#bar").style.width=`${pct}%`; $("#progressPercent").textContent=`${pct}%`;
  $("#progressMessage").textContent=`${job.message}${job.total_pages?` | page ${job.current_page.toLocaleString()} of ${job.total_pages.toLocaleString()}`:""}`;
  if(job.status==="completed"){activeJob=null;$("#indexPath").disabled=false;await refresh();setTimeout(()=>selectView("chat"),800);}
  else if(job.status==="failed"){activeJob=null;$("#indexPath").disabled=false;alert(`Indexing failed: ${job.message}`);}
  else setTimeout(pollJob,700);
}
$("#indexPath").onclick=startPath; $("#choose").onclick=()=>$("#file").click(); $("#file").onchange=e=>startUpload(e.target.files[0]);
const drop=$("#drop"); ["dragenter","dragover"].forEach(n=>drop.addEventListener(n,e=>{e.preventDefault();drop.classList.add("drag")}));
["dragleave","drop"].forEach(n=>drop.addEventListener(n,e=>{e.preventDefault();drop.classList.remove("drag")}));
drop.addEventListener("drop",e=>startUpload(e.dataTransfer.files[0]));
function appendMessage(role,text,meta=""){
  $("#welcome")?.remove(); const node=document.createElement("div"); node.className=`message ${role}`;
  node.innerHTML=`<div class="bubble">${esc(text)}</div><div class="message-meta">${esc(meta)}</div>`;
  $("#messages").appendChild(node); $("#messages").scrollTop=$("#messages").scrollHeight; return node;
}
async function ask(){
  const question=$("#question").value.trim(); if(!question)return; $("#question").value=""; $("#send").disabled=true;
  appendMessage("user",question,"You"); const waiting=appendMessage("assistant","Searching the indexed evidence...","Atlas");
  try{
    const response=await fetch("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      question,top_k:Number($("#topk").value),generate:$("#generate").checked,
      run_native_evaluators:$("#nativeEval").checked,
      generation_provider:$("#generationProvider").value,generation_model:$("#generationModel").value,
      conversation_id:conversationId})});
    const data=await responseData(response); if(!response.ok)throw new Error(data.detail||"Question failed");
    conversationId=data.conversation_id||conversationId;
    if(conversationId)sessionStorage.setItem("atlasConversationId",conversationId);
    waiting.querySelector(".bubble").textContent=data.answer;
    waiting.querySelector(".message-meta").textContent=`Atlas | ${data.citations.length} cited passages | ${data.generation_provider}/${data.generation_model} ${data.generation_status}${data.used_conversation_context?" | follow-up resolved with conversation context":""}${data.generation_note?" | "+data.generation_note:""}`;
    $("#evidence").innerHTML=data.citations.length?data.citations.map((hit,i)=>`<details ${i===0?"open":""}>
      <summary>[${i+1}] ${esc(hit.chunk.source_file)} | page ${hit.chunk.page_number}</summary>
      <div class="message-meta">Score ${hit.score.toFixed(4)} | ${esc(hit.chunk.extraction_method)} extraction | quality ${hit.chunk.quality_score.toFixed(2)} | ${hit.ranks?.bm25?`BM25 rank ${hit.ranks.bm25}`:"MMR selected"}</div>
      <div class="mini-grid">
        <div class="mini-stat"><b>${hit.score.toFixed(3)}</b><span>retrieval score</span></div>
        <div class="mini-stat"><b>${hit.chunk.page_number}</b><span>page</span></div>
        <div class="mini-stat"><b>${Math.round(hit.chunk.quality_score*100)}%</b><span>quality</span></div>
      </div>
      ${hit.visual?`<div class="visual-snapshot"><img loading="lazy" src="${esc(hit.visual.url)}" alt="${esc(hit.visual.caption)}"><div class="visual-caption">${esc(hit.visual.caption)}</div></div>`:""}
      <div class="passage">${esc(hit.chunk.text)}</div></details>`).join(""):`<div class="empty">No evidence found.</div>`;
    renderPipelineTrace(data.pipeline_trace);
    renderMetrics(data.evaluation);
  }catch(e){waiting.querySelector(".bubble").textContent=`Request failed: ${e.message}`;}
  finally{$("#send").disabled=false;}
}
$("#send").onclick=ask; $("#question").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask();}});
document.querySelectorAll(".suggestion").forEach(b=>b.onclick=()=>{$("#question").value=b.textContent;ask();});
$("#clearChat").onclick=async()=>{
  if(conversationId)await fetch(`/api/conversations/${conversationId}`,{method:"DELETE"}).catch(()=>{});
  conversationId=null;sessionStorage.removeItem("atlasConversationId");
  $("#messages").innerHTML=`<div class="welcome" id="welcome"><div class="welcome-mark">?</div><h3>Start a new research question</h3><p class="sub">Answers will remain grounded in your indexed documents.</p></div>`;
  $("#evidence").innerHTML=`<div class="empty">Citations will appear after a question.</div>`;
  $("#metrics").innerHTML=`<div class="empty" style="grid-column:1/-1">Metrics will appear after a question.</div>`;
  $("#pipelineTrace").innerHTML=`<div class="empty">Pipeline trace will appear after a question.</div>`;
  $("#providerResults").innerHTML="";
};
function pct(value){return value===null||value===undefined?"needs labels":`${Math.round(value*100)}%`;}
function metricBar(value){
  if(value===null||value===undefined)return "";
  const width=Math.max(0,Math.min(100,Math.round(value*100)));
  return `<div class="meter"><span style="width:${width}%"></span></div>`;
}
function renderPipelineTrace(trace){
  if(!trace){$("#pipelineTrace").innerHTML=`<div class="empty">No pipeline trace returned.</div>`;return;}
  const query=trace.query||{},retrieval=trace.retrieval||{},context=trace.context||{},generation=trace.generation||{},evaluation=trace.evaluation||{};
  const steps=[
    ["1. Question", query.used_memory?"memory used":"new topic", `Original: ${esc(query.original||"")}<br>Resolved: ${esc(query.resolved||"")}<br>Expansion: ${query.expansion_detected?"yes":"no"}`],
    ["2. Retrieval", retrieval.mode||"retrieval", `Top K: ${retrieval.top_k} | Candidates: ${retrieval.candidate_count} | MMR: ${retrieval.mmr_enabled?"on":"off"} | Dense: ${retrieval.dense_enabled?"on":"off"}`],
    ["3. Context", `${retrieval.citation_count||0} citations`, `Sources: ${(context.sources||[]).map(esc).join(", ")||"none"}<br>Pages: ${(context.pages||[]).map(esc).join("; ")||"none"}`],
    ["4. Generation", generation.status||"unknown", `Provider: ${esc(generation.provider||"")}<br>Model: ${esc(generation.model||"")}${generation.note?`<br>Note: ${esc(generation.note)}`:""}`],
    ["5. Evaluation", `Hit ${pct(evaluation.hit_rate_at_k)}`, `Precision: ${pct(evaluation.precision_at_k)} | nDCG: ${pct(evaluation.ndcg_at_k)} | Groundedness: ${pct(evaluation.groundedness)} | Hallucination risk: ${pct(evaluation.hallucination_risk)}`],
  ];
  $("#pipelineTrace").innerHTML=steps.map(([title,status,body])=>`<div class="pipeline-step">
    <div class="pipeline-title">${esc(title)} <span class="status-pill active">${esc(status)}</span></div>
    <div class="pipeline-body">${body}</div>
  </div>`).join("");
}
function renderMetrics(evaluation){
  if(!evaluation){$("#metrics").innerHTML=`<div class="empty" style="grid-column:1/-1">No metrics returned.</div>`;return;}
  const primary=[
    ["Precision@K proxy",evaluation.precision_at_k_proxy],
    ["Hit Rate@K proxy",evaluation.hit_rate_at_k_proxy],
    ["nDCG@K proxy",evaluation.ndcg_at_k_proxy],
    ["Groundedness",evaluation.citation_coverage],
    ["Faithfulness proxy",evaluation.groundedness],
    ["Hallucination risk",evaluation.hallucination_risk],
    ["Context relevance",evaluation.mean_context_relevance],
    ["Source diversity",evaluation.source_diversity],
  ];
  $("#metrics").innerHTML=primary.map(([name,value])=>`<div class="metric"><b>${pct(value)}</b><span>${esc(name)}</span></div>`).join("");
  const providers=evaluation.provider_results||[];
  $("#providerResults").innerHTML=providers.length?`<div class="provider-grid">${providers.map(result=>`<div class="provider-card">
    <div class="provider-head"><span>${esc(result.provider)}</span><span class="status-pill ${esc(result.status)}">${esc(result.status)}</span></div>
    <div class="provider-score">${pct(result.score)}</div>
    ${metricBar(result.score)}
    <div class="doc-meta">${esc(result.summary)}</div>
  </div>`).join("")}</div>`:`<div class="empty">Evaluator details will appear after a question.</div>`;
}
refresh();loadArchitecture();
</script>
</body>
</html>
"""
