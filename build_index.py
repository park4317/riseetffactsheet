"""
RISE ETF Factsheet - GitHub Pages Index Builder
docs/index.html 을 자동 생성합니다.
"""
import os, glob, re
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DOCS_DIR   = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# ── 생성된 팩트시트 파일 수집 ──────────────────────
files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "factsheet_*.html")), reverse=True)

# ETF별 최신 파일만 추출
latest: dict[str, dict] = {}
for path in files:
    fname = os.path.basename(path)
    m = re.match(r"factsheet_(.+)_(\d{8})\.html$", fname)
    if not m:
        continue
    etf_safe, date_str = m.group(1), m.group(2)
    etf_name = etf_safe.replace("_", " ").replace("-", "&")
    if etf_safe not in latest:
        mtime = os.path.getmtime(path)
        latest[etf_safe] = {
            "name":  etf_name,
            "file":  fname,
            "date":  f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}",
            "mtime": datetime.fromtimestamp(mtime).strftime("%Y.%m.%d %H:%M"),
            "size":  f"{os.path.getsize(path) // 1024} KB",
        }

cards = list(latest.values())
updated_at = datetime.now().strftime("%Y.%m.%d %H:%M")

# ── 카드 HTML 생성 ──────────────────────────────────
def make_card(c):
    return f"""
    <a class="card" href="output/{c['file']}" target="_blank">
      <div class="card-top">
        <span class="card-name">{c['name']}</span>
      </div>
      <div class="card-bottom">
        <span class="card-date">기준일 {c['date']}</span>
        <span class="card-size">{c['size']}</span>
      </div>
    </a>"""

cards_html = "\n".join(make_card(c) for c in cards) if cards else \
    '<p style="color:#888;text-align:center;padding:40px;">생성된 팩트시트가 없습니다.</p>'

# ── index.html ──────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RISE ETF 팩트시트 포털</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans KR',sans-serif;background:#EEF1F8;color:#111827;min-height:100vh}}
.nav{{background:#002B6E;padding:0 28px;height:54px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 12px rgba(0,0,0,.25)}}
.nav-brand{{display:flex;align-items:center;gap:10px}}
.badge{{background:#F5A800;color:#fff;font-size:10px;font-weight:900;padding:3px 8px;border-radius:3px;letter-spacing:.5px}}
.nav-title{{color:#fff;font-size:14px;font-weight:700}}
.nav-meta{{color:rgba(255,255,255,.5);font-size:11px}}
.gold-bar{{height:3px;background:linear-gradient(90deg,#F5A800 0%,#FFD66E 60%,transparent 100%)}}
.main{{max-width:1100px;margin:0 auto;padding:32px 24px}}
.page-title{{font-size:13px;font-weight:700;color:#002B6E;border-left:4px solid #F5A800;padding-left:9px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between}}
.page-title span{{font-size:11px;color:#6B7A99;font-weight:400;border:none;padding:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.card{{background:#fff;border-radius:10px;border:1px solid #E8ECF4;padding:18px 20px;text-decoration:none;display:flex;flex-direction:column;gap:10px;transition:box-shadow .18s,transform .15s}}
.card:hover{{box-shadow:0 6px 24px rgba(0,43,110,.13);transform:translateY(-2px)}}
.card-top{{display:flex;align-items:flex-start}}
.card-name{{font-size:13px;font-weight:700;color:#002B6E;line-height:1.4}}
.card-bottom{{display:flex;justify-content:space-between;align-items:center}}
.card-date{{font-size:10.5px;color:#6B7A99}}
.card-size{{font-size:10px;color:#C0C8DA;background:#F4F6FA;padding:2px 7px;border-radius:3px}}
.footer{{text-align:center;padding:32px;font-size:11px;color:#9AA5BD}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <span class="badge">RISE ETF</span>
    <span class="nav-title">팩트시트 포털</span>
  </div>
  <span class="nav-meta">최종 업데이트: {updated_at}</span>
</nav>
<div class="gold-bar"></div>
<main class="main">
  <div class="page-title">
    ETF 팩트시트 목록 ({len(cards)}개)
    <span>클릭하면 팩트시트가 열립니다</span>
  </div>
  <div class="grid">
    {cards_html}
  </div>
</main>
<footer class="footer">
  KB자산운용 RISE ETF &nbsp;|&nbsp; 이 자료는 투자권유 목적이 아닙니다 &nbsp;|&nbsp; 투자 전 설명서를 반드시 읽어보시기 바랍니다
</footer>
</body>
</html>"""

out_path = os.path.join(DOCS_DIR, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[build_index] docs/index.html 생성 완료 ({len(cards)}개 팩트시트)")
