"""
RISE ETF Factsheet - GitHub Pages Index Builder
"""
import os, glob, re
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DOCS_DIR   = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "factsheet_*.html")), reverse=True)
latest = {}
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
            "size":  f"{os.path.getsize(path) // 1024} KB",
        }

cards = list(latest.values())
updated_at = datetime.now().strftime("%Y.%m.%d %H:%M")

def make_card(c):
    name = c["name"]
    if name.startswith("RISE "):
        display = '<span class="card-rise">RISE</span> ' + name[5:]
    else:
        display = name
    cal_svg = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
    return (
        '\n    <a class="card" href="output/' + c["file"] + '" target="_blank">'
        '\n      <div class="card-accent"></div>'
        '\n      <div class="card-body">'
        '\n        <div class="card-name">' + display + '</div>'
        '\n        <div class="card-footer">'
        '\n          <span class="card-date">' + cal_svg + ' ' + c["date"] + '</span>'
        '\n          <span class="card-arrow">팩트시트 보기 &rarr;</span>'
        '\n        </div>'
        '\n      </div>'
        '\n    </a>'
    )

cards_html = "\n".join(make_card(c) for c in cards) if cards else \
    '<p style="color:#888;text-align:center;padding:40px;">생성된 팩트시트가 없습니다.</p>'

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#F0F4FA;color:#111827;min-height:100vh}
.nav{background:#002B6E;padding:0 32px;height:58px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 16px rgba(0,0,0,.3)}
.nav-brand{display:flex;align-items:center;gap:12px}
.nav-logo{background:#F5A800;color:#fff;font-size:11px;font-weight:900;padding:4px 10px;border-radius:4px;letter-spacing:.8px}
.nav-sub{color:rgba(255,255,255,.45);font-size:11px}
.gold-bar{height:3px;background:linear-gradient(90deg,#F5A800 0%,#FFD66E 50%,rgba(245,168,0,0) 100%)}
.main{max-width:1120px;margin:0 auto;padding:36px 24px}
.header-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.section-title{font-size:15px;font-weight:700;color:#002B6E;display:flex;align-items:center;gap:8px}
.section-title::before{content:'';display:inline-block;width:4px;height:18px;background:#F5A800;border-radius:2px}
.count-badge{background:#002B6E;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:20px}
.update-time{font-size:11px;color:#8A97B4}
.search-wrap{position:relative;margin-bottom:24px}
.search-icon{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:#8A97B4}
.search-input{width:100%;border:1.5px solid #DCE3F0;border-radius:8px;padding:10px 14px 10px 36px;font-size:12.5px;font-family:inherit;outline:none;background:#fff;color:#111827;transition:border-color .2s}
.search-input:focus{border-color:#002B6E;box-shadow:0 0 0 3px rgba(0,43,110,.08)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.no-result{text-align:center;padding:40px;color:#9AA5BD;font-size:12px;display:none;grid-column:1/-1}
.card{background:#fff;border-radius:12px;border:1px solid #E2E8F4;text-decoration:none;display:flex;overflow:hidden;transition:box-shadow .2s,transform .15s}
.card:hover{box-shadow:0 8px 28px rgba(0,43,110,.14);transform:translateY(-3px)}
.card-accent{width:5px;background:#002B6E;flex-shrink:0;transition:background .2s}
.card:hover .card-accent{background:#F5A800}
.card-body{flex:1;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
.card-name{font-size:13.5px;font-weight:700;color:#002B6E;line-height:1.45}
.card-rise{font-size:10px;font-weight:900;background:#002B6E;color:#F5A800;padding:2px 6px;border-radius:3px;letter-spacing:.5px;vertical-align:middle;margin-right:2px}
.card-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto}
.card-date{font-size:11px;color:#8A97B4;display:flex;align-items:center;gap:4px}
.card-arrow{font-size:11px;font-weight:600;color:#F5A800;opacity:0;transition:opacity .2s}
.card:hover .card-arrow{opacity:1}
.footer{text-align:center;padding:36px;font-size:11px;color:#9AA5BD;margin-top:8px}
.footer strong{color:#002B6E}"""

JS = """function filterCards() {
  var q = document.getElementById('searchInput').value.toLowerCase();
  var cards = document.querySelectorAll('#cardGrid .card');
  var visible = 0;
  cards.forEach(function(c) {
    var name = c.querySelector('.card-name').textContent.toLowerCase();
    if (!q || name.includes(q)) { c.style.display = ''; visible++; }
    else { c.style.display = 'none'; }
  });
  document.getElementById('noResult').style.display = visible === 0 ? 'block' : 'none';
}"""

SEARCH_ICON = '<svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'

html = (
    '<!DOCTYPE html>\n<html lang="ko">\n<head>\n'
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    '<title>RISE ETF 팩트시트</title>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;900&display=swap" rel="stylesheet">\n'
    '<style>\n' + CSS + '\n</style>\n</head>\n<body>\n'
    '<nav class="nav">\n'
    '  <div class="nav-brand"><span class="nav-logo">RISE ETF</span></div>\n'
    '  <span class="nav-sub">최종 업데이트: ' + updated_at + '</span>\n'
    '</nav>\n'
    '<div class="gold-bar"></div>\n'
    '<main class="main">\n'
    '  <div class="header-row">\n'
    '    <div class="section-title">ETF 목록(국내주식형)<span class="count-badge">' + str(len(cards)) + '개</span></div>\n'
    '    <span class="update-time">기준일 ' + updated_at[:10] + '</span>\n'
    '  </div>\n'
    '  <div class="search-wrap">\n'
    '    ' + SEARCH_ICON + '\n'
    '    <input class="search-input" type="text" id="searchInput" placeholder="ETF 이름 검색 (예: 네트워크, AI, 배당)" oninput="filterCards()">\n'
    '  </div>\n'
    '  <div class="grid" id="cardGrid">\n'
    + cards_html +
    '\n    <div class="no-result" id="noResult">검색 결과가 없습니다</div>\n'
    '  </div>\n</main>\n'
    '<script>\n' + JS + '\n</script>\n'
    '<footer class="footer"><strong>KB자산운용 RISE ETF</strong> &nbsp;|&nbsp; 이 자료는 투자권유 목적이 아닙니다 &nbsp;|&nbsp; 투자 전 설명서를 반드시 읽어보시기 바랍니다</footer>\n'
    '</body>\n</html>'
)

out_path = os.path.join(DOCS_DIR, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"[build_index] 완료: {len(cards)}개 팩트시트")
