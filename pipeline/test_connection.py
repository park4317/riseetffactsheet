# ============================================================
#  연결 테스트 스크립트 — PC에서 실행하세요
#  실행: python test_connection.py
# ============================================================

import requests
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Referer": "https://www.riseetf.co.kr/",
}

SITE_ID = "44K4"  # RISE 현대차고정피지컬AI
BASE    = "https://www.riseetf.co.kr"

session = requests.Session()
session.headers.update(HEADERS)

def read_as_table(content: bytes) -> pd.DataFrame | None:
    """
    HTML-as-Excel 패턴 처리:
    한국 금융사이트는 Excel 다운로드라도 실제로는 HTML 테이블을 내려줌.
    1) pd.read_html() 시도 → 2) pd.read_excel() 시도 순서로 파싱.
    """
    # ① HTML 테이블로 파싱 (가장 흔한 패턴)
    try:
        tables = pd.read_html(BytesIO(content), encoding="utf-8")
        if tables:
            return tables[0]
    except Exception:
        pass

    # ② 진짜 Excel 파일인 경우
    for engine in ("openpyxl", "xlrd"):
        try:
            return pd.read_excel(BytesIO(content), header=None, engine=engine)
        except Exception:
            pass

    return None


def test(label, url, parser="excel"):
    print(f"\n{'─'*55}")
    print(f"  {label}")
    print(f"  URL: {url}")
    try:
        r = session.get(url, timeout=15)
        ctype = r.headers.get("Content-Type", "")
        print(f"  Status: {r.status_code} | {len(r.content):,} bytes | {ctype}")

        if r.status_code != 200:
            print(f"  ❌ 실패 — 응답 일부: {r.text[:200]}")
            return

        if parser == "excel":
            df = read_as_table(r.content)
            if df is not None:
                print(f"  ✅ 파싱 성공! {df.shape[0]}행 × {df.shape[1]}열")
                print(df.to_string(max_rows=25, max_cols=8))
            else:
                print(f"  ❌ 파싱 실패 — 첫 300바이트: {r.content[:300]}")

        elif parser == "html":
            soup = BeautifulSoup(r.content, "lxml")
            tables = soup.find_all("table")
            print(f"  ✅ HTML 수신 성공! 테이블 {len(tables)}개 발견")
            for i, t in enumerate(tables):
                rows = t.find_all("tr")
                first_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th","td"])] if rows else []
                print(f"    table[{i}]: {len(rows)}행, 첫 행={first_cells[:6]}")

    except Exception as e:
        print(f"  ❌ 오류: {e}")


print("=" * 55)
print("  RISE ETF 데이터 연결 테스트")
print("=" * 55)

test("① 기본정보 Excel",
     f"{BASE}/prod/finder/productViewTabExcel1?searchTargetId={SITE_ID}")

test("② 일별 NAV Excel",
     f"{BASE}/prod/finder/productViewTabExcel2?searchTargetId={SITE_ID}"
     f"&searchStartDate=2026-05-01&searchEndDate=2026-06-05")

test("③ 수익률 Excel",
     f"{BASE}/prod/finder/producProfitTabExcel2?searchTargetId={SITE_ID}")

test("④ 상세 페이지 HTML (구성종목)",
     f"{BASE}/prod/finderDetail/{SITE_ID}",
     parser="html")

print("\n" + "=" * 55)
print("  ✅ 테스트 완료! 위 결과를 JK님이 확인 후 공유해주세요.")
print("  — ✅ 이면 해당 소스 그대로 사용")
print("  — ❌ 이면 대안 방식으로 전환")
print("=" * 55)
