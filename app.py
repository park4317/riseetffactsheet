# ============================================================
#  RISE ETF 팩트시트 자동화 — 웹 대시보드
#
#  실행:  python app.py
#  접속:  http://localhost:5100
# ============================================================

import sys
import os
import glob
import threading
import json
from datetime import datetime

from flask import Flask, jsonify, send_file, abort, Response

# pipeline 폴더 임포트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pipeline"))

from config import ETF_LIST

# 출력 폴더 (프로젝트 루트 기준)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

# 생성 상태 저장 (메모리, 프로세스 재시작 시 초기화)
_status: dict[str, dict] = {}
_status_lock = threading.Lock()


# ──────────────────────────────────────────────────
#  대시보드 HTML (임베디드)
# ──────────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RISE ETF 팩트시트 자동화 시스템</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;900&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --blue-dark: #002B6E; --blue-mid: #0047B3; --blue-light: #E8F0FD;
  --gold: #F5A800; --gold-light: #FFF8E0;
  --red: #E03232; --green: #0A7C42;
  --gray-1: #F4F6FA; --gray-2: #E8ECF4; --gray-3: #C0C8DA;
  --gray-text: #6B7A99; --text-main: #111827; --text-sub: #374151;
  --sidebar-w: 260px;
}
body {
  font-family: 'Noto Sans KR', sans-serif;
  background: #EFF2F8;
  color: var(--text-main);
  font-size: 13px;
  line-height: 1.5;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── TOP NAVBAR ── */
.navbar {
  background: var(--blue-dark);
  padding: 0 28px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(0,0,0,.25);
}
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-badge {
  background: var(--gold);
  color: #fff;
  font-size: 10px;
  font-weight: 900;
  padding: 3px 8px;
  border-radius: 3px;
  letter-spacing: .5px;
}
.brand-title {
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -.2px;
}
.navbar-meta {
  color: rgba(255,255,255,.5);
  font-size: 11px;
}
.gold-bar {
  height: 3px;
  background: linear-gradient(90deg, var(--gold) 0%, #FFD66E 60%, transparent 100%);
}

/* ── MAIN CONTENT ── */
.main {
  flex: 1;
  padding: 28px 32px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* ── SECTION HEADER ── */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--blue-dark);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background: var(--gold);
  border-radius: 2px;
  display: inline-block;
}
.btn-all {
  background: var(--blue-dark);
  color: #fff;
  border: none;
  padding: 7px 16px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  transition: background .15s;
}
.btn-all:hover { background: var(--blue-mid); }
.btn-all:disabled { background: var(--gray-3); cursor: not-allowed; }

/* ── ETF GRID ── */
.etf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 36px;
}

/* ── ETF CARD ── */
.etf-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,.07);
  overflow: hidden;
  transition: box-shadow .2s, transform .15s;
  border: 1px solid var(--gray-2);
}
.etf-card:hover {
  box-shadow: 0 6px 24px rgba(0,43,110,.12);
  transform: translateY(-2px);
}
.card-header {
  background: var(--blue-dark);
  padding: 14px 18px 12px;
  position: relative;
  overflow: hidden;
}
.card-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--gold) 0%, #FFD66E 60%, transparent 100%);
}
.card-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.tag {
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.2);
  color: rgba(255,255,255,.85);
  font-size: 9.5px;
  padding: 2px 7px;
  border-radius: 20px;
  font-weight: 500;
}
.tag.accent {
  background: var(--gold);
  border-color: var(--gold);
  color: #fff;
  font-weight: 700;
}
.card-name {
  color: #fff;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: -.2px;
  line-height: 1.3;
}
.card-ticker {
  color: rgba(255,255,255,.45);
  font-size: 10px;
  margin-left: 6px;
  font-weight: 400;
}
.card-body {
  padding: 14px 18px;
}
.card-desc {
  font-size: 11px;
  color: var(--text-sub);
  line-height: 1.55;
  margin-bottom: 12px;
  min-height: 32px;
}
.card-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.meta-badge {
  background: var(--blue-light);
  color: var(--blue-mid);
  font-size: 9.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}
.last-gen {
  font-size: 10px;
  color: var(--gray-text);
  display: flex;
  align-items: center;
  gap: 4px;
}
.last-gen .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  display: inline-block;
  flex-shrink: 0;
}
.last-gen .dot.none { background: var(--gray-3); }
.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.btn-generate {
  flex: 1;
  background: var(--blue-mid);
  color: #fff;
  border: none;
  padding: 9px 14px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s, opacity .15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn-generate:hover { background: #003A9A; }
.btn-generate:disabled { background: var(--gray-3); cursor: not-allowed; }
.btn-generate.running {
  background: #6B7A99;
  cursor: not-allowed;
}
.btn-view {
  background: var(--gold-light);
  color: #8A6200;
  border: 1px solid #FFD066;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: background .15s;
  white-space: nowrap;
}
.btn-view:hover { background: #FFE89A; }
.btn-view.hidden { display: none; }

/* ── SPINNER ── */
.spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  display: none;
}
.running .spinner { display: block; }

@keyframes spin { to { transform: rotate(360deg); } }

/* ── PROGRESS BAR ── */
.progress-bar {
  height: 3px;
  background: var(--gray-2);
  border-radius: 0 0 10px 10px;
  overflow: hidden;
  display: none;
}
.progress-bar.active { display: block; }
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--gold), #FFD066);
  border-radius: 3px;
  animation: progress-indeterminate 1.4s ease-in-out infinite;
  transform-origin: 0 50%;
}
@keyframes progress-indeterminate {
  0% { transform: translateX(-100%) scaleX(0.3); }
  50% { transform: translateX(0%) scaleX(0.6); }
  100% { transform: translateX(200%) scaleX(0.3); }
}

/* ── STATUS MESSAGE ── */
.status-msg {
  font-size: 10px;
  color: var(--gray-text);
  margin-top: 6px;
  min-height: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-msg.error { color: var(--red); }
.status-msg.success { color: var(--green); }

/* ── REPORTS TABLE ── */
.reports-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid var(--gray-2);
  box-shadow: 0 2px 12px rgba(0,0,0,.05);
  overflow: hidden;
  margin-bottom: 28px;
}
.reports-table {
  width: 100%;
  border-collapse: collapse;
}
.reports-table th {
  background: var(--blue-dark);
  color: rgba(255,255,255,.8);
  font-size: 10px;
  font-weight: 600;
  padding: 9px 16px;
  text-align: left;
  letter-spacing: .3px;
}
.reports-table td {
  padding: 10px 16px;
  font-size: 11.5px;
  border-bottom: 1px solid var(--gray-2);
  color: var(--text-sub);
}
.reports-table tr:last-child td { border-bottom: none; }
.reports-table tr:hover td { background: var(--gray-1); }
.file-link {
  color: var(--blue-mid);
  text-decoration: none;
  font-weight: 600;
}
.file-link:hover { text-decoration: underline; }
.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--gray-text);
  font-size: 12px;
}

/* ── TOAST ── */
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 9999;
}
.toast {
  background: #fff;
  border-left: 4px solid var(--blue-mid);
  border-radius: 6px;
  padding: 12px 16px;
  min-width: 260px;
  box-shadow: 0 4px 20px rgba(0,0,0,.15);
  animation: toast-in .25s ease;
  font-size: 12px;
}
.toast.success { border-color: var(--green); }
.toast.error   { border-color: var(--red); }
.toast-title { font-weight: 700; margin-bottom: 2px; color: var(--text-main); }
.toast-body  { color: var(--gray-text); }
@keyframes toast-in {
  from { opacity:0; transform: translateX(20px); }
  to   { opacity:1; transform: translateX(0); }
}
</style>
</head>
<body>

<nav class="navbar">
  <div class="navbar-brand">
    <span class="brand-badge">RISE ETF</span>
    <span class="brand-title">팩트시트 자동화 시스템</span>
  </div>
  <span class="navbar-meta" id="nowLabel"></span>
</nav>
<div class="gold-bar"></div>

<main class="main">

  <!-- ETF 목록 -->
  <div class="section-header">
    <div class="section-title">ETF 팩트시트 생성</div>
    <button class="btn-all" id="btnAll" onclick="generateAll()">
      ⚡ 전체 일괄 생성
    </button>
  </div>

  <div class="etf-grid" id="etfGrid">
    <div style="padding:40px; text-align:center; color:var(--gray-text); grid-column:1/-1;">
      불러오는 중...
    </div>
  </div>

  <!-- 생성 이력 -->
  <div class="section-header">
    <div class="section-title">생성된 리포트 목록</div>
    <button class="btn-all" onclick="loadReports()" style="background:var(--gray-text);">
      🔄 새로고침
    </button>
  </div>
  <div class="reports-section">
    <table class="reports-table">
      <thead>
        <tr>
          <th>파일명</th>
          <th>생성일시</th>
          <th>크기</th>
          <th>열기</th>
        </tr>
      </thead>
      <tbody id="reportsBody">
        <tr><td colspan="4" class="empty-state">생성된 리포트가 없습니다</td></tr>
      </tbody>
    </table>
  </div>

</main>

<div class="toast-container" id="toastContainer"></div>

<script>
// ── 현재 시간 ─────────────────────────────────────
(function tick() {
  const el = document.getElementById('nowLabel');
  if (el) el.textContent = new Date().toLocaleString('ko-KR', {hour12:false}) + ' 기준';
  setTimeout(tick, 1000);
})();

// ── ETF 카드 렌더 ──────────────────────────────────
async function loadEtfs() {
  const resp = await fetch('/api/etfs');
  const etfs = await resp.json();
  const grid = document.getElementById('etfGrid');

  if (!etfs.length) {
    grid.innerHTML = '<div style="padding:40px;text-align:center;color:var(--gray-text);grid-column:1/-1;">등록된 ETF가 없습니다 (config.py 확인)</div>';
    return;
  }

  grid.innerHTML = etfs.map(e => cardHTML(e)).join('');
  // 상태 폴링 시작
  etfs.forEach(e => { if (e.status === 'running') startPolling(e.name); });
}

function cardHTML(e) {
  const id = etfCardId(e.name);
  const tags = (e.keywords||[]).slice(0,4).map((k,i) =>
    `<span class="tag${i===0?' accent':''}">${k}</span>`).join('');
  const lastGen = e.last_gen
    ? `<span class="dot"></span> 최근 생성: ${e.last_gen}`
    : `<span class="dot none"></span> 미생성`;
  const viewBtn = e.last_file
    ? `<a class="btn-view" href="/output/${e.last_file}" target="_blank">📄 보기</a>`
    : `<a class="btn-view hidden" href="#" target="_blank">📄 보기</a>`;
  const isRunning = e.status === 'running';

  return `
<div class="etf-card" id="${id}">
  <div class="card-header">
    <div class="card-tags">${tags}</div>
    <div class="card-name">${e.name}<span class="card-ticker">${e.ticker}</span></div>
  </div>
  <div class="card-body">
    <div class="card-desc">${e.description || '—'}</div>
    <div class="card-meta">
      <span class="meta-badge">${e.category||'—'}</span>
      <span class="last-gen" id="${id}-lastgen">${lastGen}</span>
    </div>
    <div class="card-actions">
      <button class="btn-generate${isRunning?' running':''}"
              id="${id}-btn"
              onclick="generate('${e.name}')"
              ${isRunning?'disabled':''}>
        <div class="spinner" id="${id}-spinner"></div>
        <span id="${id}-btnlabel">${isRunning?'생성 중...':'📊 팩트시트 생성'}</span>
      </button>
      <span id="${id}-view">${viewBtn}</span>
    </div>
    <div class="status-msg" id="${id}-msg"></div>
  </div>
  <div class="progress-bar${isRunning?' active':''}" id="${id}-bar">
    <div class="progress-fill"></div>
  </div>
</div>`;
}

function etfCardId(name) {
  return 'card-' + name.replace(/[^a-zA-Z0-9가-힣]/g, '_');
}

// ── 팩트시트 생성 ───────────────────────────────────
async function generate(name) {
  const id = etfCardId(name);
  setRunning(id, name, true);

  try {
    const resp = await fetch(`/api/generate/${encodeURIComponent(name)}`, {method:'POST'});
    const data = await resp.json();
    if (data.status === 'running') {
      startPolling(name);
    } else if (data.error) {
      setRunning(id, name, false);
      setMsg(id, data.error, 'error');
    }
  } catch(e) {
    setRunning(id, name, false);
    setMsg(id, '네트워크 오류: ' + e.message, 'error');
  }
}

const _pollers = {};
function startPolling(name) {
  if (_pollers[name]) return;
  const id = etfCardId(name);
  setRunning(id, name, true);
  _pollers[name] = setInterval(async () => {
    try {
      const resp = await fetch(`/api/status/${encodeURIComponent(name)}`);
      const st   = await resp.json();
      if (st.status === 'done') {
        clearInterval(_pollers[name]);
        delete _pollers[name];
        setRunning(id, name, false);
        // 보기 버튼 업데이트
        if (st.output) {
          document.getElementById(`${id}-view`).innerHTML =
            `<a class="btn-view" href="/output/${st.output}" target="_blank">📄 보기</a>`;
          document.getElementById(`${id}-lastgen`).innerHTML =
            `<span class="dot"></span> 방금 생성됨`;
        }
        setMsg(id, '✅ 생성 완료', 'success');
        showToast(name, '팩트시트가 생성되었습니다', 'success');
        loadReports();
      } else if (st.status === 'error') {
        clearInterval(_pollers[name]);
        delete _pollers[name];
        setRunning(id, name, false);
        setMsg(id, '❌ ' + (st.message || '오류 발생'), 'error');
        showToast(name, st.message || '생성 오류', 'error');
      }
    } catch(e) {
      // 일시적 네트워크 오류, 계속 폴링
    }
  }, 2000);
}

function setRunning(id, name, on) {
  const btn = document.getElementById(`${id}-btn`);
  const bar = document.getElementById(`${id}-bar`);
  if (!btn) return;
  if (on) {
    btn.classList.add('running');
    btn.disabled = true;
    document.getElementById(`${id}-btnlabel`).textContent = '생성 중...';
    if (bar) bar.classList.add('active');
  } else {
    btn.classList.remove('running');
    btn.disabled = false;
    document.getElementById(`${id}-btnlabel`).textContent = '📊 팩트시트 생성';
    if (bar) bar.classList.remove('active');
  }
}

function setMsg(id, text, type='') {
  const el = document.getElementById(`${id}-msg`);
  if (!el) return;
  el.textContent = text;
  el.className = 'status-msg' + (type ? ' ' + type : '');
}

// ── 전체 일괄 생성 ──────────────────────────────────
async function generateAll() {
  const btn = document.getElementById('btnAll');
  btn.disabled = true;
  btn.textContent = '생성 중...';
  const resp = await fetch('/api/etfs');
  const etfs = await resp.json();
  for (const e of etfs) {
    await generate(e.name);
    await new Promise(r => setTimeout(r, 500));
  }
  btn.disabled = false;
  btn.innerHTML = '⚡ 전체 일괄 생성';
}

// ── 리포트 목록 ─────────────────────────────────────
async function loadReports() {
  const resp = await fetch('/api/reports');
  const files = await resp.json();
  const tbody = document.getElementById('reportsBody');
  if (!files.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">생성된 리포트가 없습니다</td></tr>';
    return;
  }
  tbody.innerHTML = files.map(f => `
    <tr>
      <td style="font-size:11px; font-family:monospace;">${f.name}</td>
      <td>${f.mtime}</td>
      <td style="color:var(--gray-text);">${f.size}</td>
      <td><a class="file-link" href="/output/${f.name}" target="_blank">열기 →</a></td>
    </tr>`).join('');
}

// ── 토스트 알림 ─────────────────────────────────────
function showToast(title, body, type='') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.innerHTML = `<div class="toast-title">${title}</div><div class="toast-body">${body}</div>`;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transition='opacity .4s';
    setTimeout(() => t.remove(), 400); }, 3500);
}

// ── 초기화 ──────────────────────────────────────────
loadEtfs();
loadReports();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────
#  API 라우트
# ──────────────────────────────────────────────────

@app.route("/")
def index():
    return DASHBOARD_HTML


@app.route("/api/etfs")
def api_etfs():
    etfs = []
    for name, cfg in ETF_LIST.items():
        safe = name.replace(" ", "_").replace("/", "-")
        pattern = os.path.join(OUTPUT_DIR, f"factsheet_{safe}_*.html")
        files = sorted(glob.glob(pattern))
        last_gen = last_file = None
        if files:
            mtime = os.path.getmtime(files[-1])
            last_gen = datetime.fromtimestamp(mtime).strftime("%Y.%m.%d %H:%M")
            last_file = os.path.basename(files[-1])

        with _status_lock:
            st = _status.get(name, {}).get("status", "idle")

        etfs.append({
            "name":        name,
            "ticker":      cfg.get("ticker", ""),
            "category":    cfg.get("category", "—"),
            "description": cfg.get("description", ""),
            "keywords":    cfg.get("keywords", []),
            "last_gen":    last_gen,
            "last_file":   last_file,
            "status":      st,
        })
    return jsonify(etfs)


@app.route("/api/generate/<path:etf_name>", methods=["POST"])
def api_generate(etf_name):
    if etf_name not in ETF_LIST:
        return jsonify({"error": f"'{etf_name}' 이 config.py에 없습니다"}), 404

    with _status_lock:
        if _status.get(etf_name, {}).get("status") == "running":
            return jsonify({"status": "running", "message": "이미 생성 중입니다"})
        _status[etf_name] = {"status": "running", "ts": datetime.now().isoformat()}

    def _run():
        try:
            # pipeline/ 폴더 기준으로 작업 디렉터리 임시 변경
            orig_dir = os.getcwd()
            pipeline_dir = os.path.join(os.path.dirname(__file__), "pipeline")
            os.chdir(pipeline_dir)
            try:
                from main import generate_factsheet
                result = generate_factsheet(etf_name)
            finally:
                os.chdir(orig_dir)

            if result and result.get("output"):
                out_fname = os.path.basename(result["output"])
                with _status_lock:
                    _status[etf_name] = {
                        "status": "done",
                        "output": out_fname,
                        "ts":     datetime.now().isoformat(),
                    }
            else:
                with _status_lock:
                    _status[etf_name] = {"status": "error", "message": "generate_factsheet 반환값 없음"}
        except Exception as e:
            with _status_lock:
                _status[etf_name] = {"status": "error", "message": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "running"})


@app.route("/api/status/<path:etf_name>")
def api_status(etf_name):
    with _status_lock:
        return jsonify(_status.get(etf_name, {"status": "idle"}))


@app.route("/api/reports")
def api_reports():
    files = []
    for path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "factsheet_*.html")), reverse=True):
        stat = os.stat(path)
        size = stat.st_size
        size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
        files.append({
            "name":  os.path.basename(path),
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y.%m.%d %H:%M"),
            "size":  size_str,
        })
    return jsonify(files)


@app.route("/output/<filename>")
def serve_output(filename):
    # path traversal 방어
    safe = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, safe)
    if not os.path.exists(path):
        abort(404)
    return send_file(path)


# ──────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5100))
    print(f"\n{'='*55}")
    print(f"  RISE ETF 팩트시트 자동화 시스템")
    print(f"  접속 주소: http://localhost:{port}")
    print(f"{'='*55}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
