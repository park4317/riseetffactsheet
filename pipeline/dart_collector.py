# ============================================================
#  DART API 기반 분배금 이력 수집기
#  opendart.fss.or.kr — 무료 공개 API
#
#  수집 흐름:
#    1. KB자산운용 corp_code 조회 (캐시)
#    2. 펀드공시(pblntf_ty=G) 중 분배금 보고서 목록 수집
#    3. 보고서 본문에서 ETF 티커·분배금액 파싱
# ============================================================

import re
import json
import requests
from datetime import datetime, timedelta

BASE = "https://opendart.fss.or.kr/api"

# KB자산운용 corp_code 캐시 (최초 1회 API 조회 후 저장)
_CORP_CODE_CACHE: dict[str, str] = {}


class DARTCollector:
    def __init__(self, api_key: str):
        self.key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })

    # ── 1. KB자산운용 corp_code 조회 ─────────────────────────
    def get_corp_code(self, corp_name: str = "케이비자산운용") -> str:
        """
        KB자산운용 corp_code 조회.
        DART company.json은 정확한 법인명이 필요 → 복수 후보명으로 순차 시도.
        실패 시 corp_list.xml(전체 목록)에서 검색.
        """
        # 캐시 확인
        cache_key = "KB_AM"
        if cache_key in _CORP_CODE_CACHE:
            return _CORP_CODE_CACHE[cache_key]

        # 시도할 회사명 후보
        candidates = ["케이비자산운용", "KB자산운용", "케이비(KB)자산운용", "KB Asset Management"]
        for name in candidates:
            try:
                r = self.session.get(
                    f"{BASE}/company.json",
                    params={"crtfc_key": self.key, "corp_name": name},
                    timeout=10,
                )
                data = r.json()
                if data.get("status") == "000":
                    code = data.get("corp_code", "")
                    if code:
                        _CORP_CODE_CACHE[cache_key] = code
                        print(f"  [DART] corp_code={code} ({name})")
                        return code
            except Exception as e:
                print(f"  [DART] corp_code 조회 실패 ({name}): {e}")

        # 최후 수단: corp_list.xml 전체 다운로드 후 "KB" 검색
        try:
            import zipfile, io, xml.etree.ElementTree as ET
            r = self.session.get(
                f"{BASE}/corpCode.xml",
                params={"crtfc_key": self.key},
                timeout=30,
            )
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                xml_data = z.read(z.namelist()[0])
            root = ET.fromstring(xml_data)
            for item in root.findall("list"):
                name_el = item.find("corp_name")
                if name_el is not None and "자산운용" in name_el.text and "KB" in name_el.text:
                    code = item.find("corp_code").text
                    print(f"  [DART] XML에서 발견: {name_el.text} → {code}")
                    _CORP_CODE_CACHE[cache_key] = code
                    return code
        except Exception as e:
            print(f"  [DART] corp_list.xml 조회 실패: {e}")

        print("  [DART] KB자산운용 corp_code를 찾을 수 없음")
        return ""

    # ── 2. 분배금 공시 목록 조회 ─────────────────────────────
    def get_dist_report_list(self, corp_code: str, years: int = 3) -> list[dict]:
        """
        pblntf_ty=G(펀드공시) 중 '분배' 키워드 보고서 목록 반환
        각 item: {rcept_no, rcept_dt, report_nm}
        """
        bgn = (datetime.now() - timedelta(days=365 * years)).strftime("%Y%m%d")
        end = datetime.now().strftime("%Y%m%d")
        try:
            r = self.session.get(
                f"{BASE}/list.json",
                params={
                    "crtfc_key": self.key,
                    "corp_code":  corp_code,
                    "bgn_de":     bgn,
                    "end_de":     end,
                    "pblntf_ty":  "G",    # 펀드공시
                    "page_count": 100,
                },
                timeout=15,
            )
            data = r.json()
            if data.get("status") not in ("000", "013"):
                print(f"  [DART] 공시목록 오류: {data.get('message','')}")
                return []
            # "분배금 지급" 공시만 필터 — 펀드명에 "배당"이 들어간 다른 보고서 제외
            DIST_KEYWORDS = ["분배금 지급", "분배금지급", "집합투자기구 분배"]
            reports = [
                item for item in data.get("list", [])
                if any(kw in item.get("report_nm", "") for kw in DIST_KEYWORDS)
            ]
            print(f"  [DART] 분배금 지급 공시 {len(reports)}건 발견")
            import os as _os
            if _os.environ.get("DART_DEBUG"):
                for rp in reports[:5]:
                    print(f"    {rp.get('rcept_dt','')} | {rp.get('report_nm','')}")
            return reports
        except Exception as e:
            print(f"  [DART] 공시목록 조회 실패: {e}")
            return []

    # ── 3. 보고서 본문에서 날짜·금액 파싱 ────────────────────
    def parse_report_detail(self, rcept_no: str, etf_ticker: str) -> dict | None:
        """
        document.json → 보고서 본문 HTML에서
        분배기준일 + 1주당 분배금 파싱
        returns {"date": "YYYY.MM.DD", "amount": float} or None
        """
        try:
            r = self.session.get(
                f"{BASE}/document.json",
                params={"crtfc_key": self.key, "rcept_no": rcept_no},
                timeout=15,
            )
            data = r.json()
            if data.get("status") != "000":
                return None

            html = data.get("body", "")

            # ── 진단 (DART_DEBUG=1 시 출력) ──────────────────
            import os as _os
            if _os.environ.get("DART_DEBUG"):
                idx = html.find("분배기준일")
                if idx < 0: idx = html.find("분배 기준일")
                if idx >= 0:
                    print(f"    [DART DEBUG] 분배기준일 주변: {html[max(0,idx-30):idx+150]!r}")
                else:
                    print(f"    [DART DEBUG] '분배기준일' 없음, 본문({len(html)}자): {html[:300]!r}")

            # 티커가 본문에 없으면 ETF 이름으로 재시도 후 skip
            if etf_ticker and etf_ticker not in html:
                # 펀드 등록명은 티커 대신 "RISE XXX" 또는 "코스피200" 형태일 수 있음
                # → 티커 체크 완화: 이름 힌트 없이도 분배기준일이 있으면 허용
                if "분배기준일" not in html and "분배 기준일" not in html:
                    return None  # 분배 관련 내용 자체가 없음 → skip

            # 분배기준일 파싱
            date_m = re.search(
                r'분배\s*기준\s*일[^\d]*(\d{4}[.\-/년]\d{1,2}[.\-/월]\d{1,2})',
                html
            )
            date_str = None
            if date_m:
                raw = date_m.group(1)
                parts = re.split(r'[.\-/년월일]', raw)
                parts = [p.zfill(2) for p in parts if p]
                if len(parts) >= 3:
                    date_str = f"{parts[0]}.{parts[1]}.{parts[2]}"

            amt_m = re.search(
                r'1\s*주\s*당\s*분배\s*금[^\d]*([0-9,]+(?:\.\d+)?)\s*원',
                html
            )
            amount = None
            if amt_m:
                try:
                    amount = float(amt_m.group(1).replace(",", ""))
                except ValueError:
                    pass

            if date_str:
                return {"date": date_str, "amount": amount}
        except Exception as e:
            print(f"  [DART] 보고서 파싱 오류 ({rcept_no}): {e}")
        return None

    def get_distribution_history(self, etf_ticker: str, etf_name: str,
                                  years: int = 3) -> list[dict]:
        corp_code = self.get_corp_code()
        if not corp_code:
            print(f"  [DART] corp_code 없음 -> 분배금 수집 불가")
            return []
        reports = self.get_dist_report_list(corp_code, years=years)
        if not reports:
            return []
        records = []
        seen_dates = set()
        for report in reports:
            rcept_no = report.get("rcept_no", "")
            detail = self.parse_report_detail(rcept_no, etf_ticker)
            if detail and detail["date"] not in seen_dates:
                seen_dates.add(detail["date"])
                records.append(detail)
        records = sorted(records, key=lambda x: x["date"], reverse=True)
        for r in records[:3]:
            amt_str = f"{int(r['amount'])}원" if r.get("amount") else "금액미확인"
            print(f"    {r['date']} {amt_str}")
        print(f"  [DART] {etf_name} 분배금 {len(records)}건")
        return records
