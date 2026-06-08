# ============================================================
#  KRX 데이터 수집기
#  - 전종목 시장구분(KOSPI/KOSDAQ) + 업종: MDCSTAT01901 1회 일괄 조회
#  - BM 지수 데이터: yfinance
# ============================================================

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False
    print("[경고] yfinance 미설치 → pip install yfinance")

import re
import json as _json
import requests as _req
from datetime import datetime, timedelta

# ── KRX OpenAPI 공통 ──────────────────────────────────────────
_KRX_OPEN_BASE = "https://openapi.krx.co.kr"

_KRX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}
# Referer/Origin 제거 — openapi.krx.co.kr WAF가 mismatch 차단함


def _krx_otp(bld: str, api_key: str, extra: dict = None) -> str:
    """KRX OTP 발급 공통 함수"""
    params = {"bld": bld, "auth": api_key}
    if extra:
        params.update(extra)
    try:
        r = _req.post(
            f"{_KRX_OPEN_BASE}/contents/COM/GenerateOTP.jspx",
            data=params,
            headers=_KRX_HEADERS,
            timeout=15,
        )
        otp = r.text.strip()
        return otp if otp and len(otp) >= 10 else ""
    except Exception as e:
        print(f"  [KRX OTP 오류] {bld}: {e}")
        return ""


def _krx_query(endpoint: str, otp: str, extra_data: dict = None) -> list[dict]:
    """KRX OTP로 데이터 조회 공통 함수"""
    body = {"code": otp}
    if extra_data:
        body.update(extra_data)
    try:
        r = _req.post(
            f"{_KRX_OPEN_BASE}/contents/MDC/STAT/standard/{endpoint}.cmd",
            data=body,
            headers=_KRX_HEADERS,
            timeout=30,
        )
        raw = r.text.strip()
        if not raw:
            print(f"  [KRX] {endpoint} 응답 비어있음 (HTTP {r.status_code})")
            return []
        resp = _json.loads(raw)
        return resp.get("output", resp.get("OutBlock_1", []))
    except _json.JSONDecodeError as e:
        preview = r.text[:120].replace("\n", " ")
        print(f"  [KRX 쿼리 오류] {endpoint}: JSON 파싱 실패 | 응답: {preview!r}")
        return []
    except Exception as e:
        print(f"  [KRX 쿼리 오류] {endpoint}: {e}")
        return []


# ── KRX 전종목 시장+업종 캐시 ────────────────────────────────
_KRX_STOCK_CACHE: dict[str, dict] = {}  # ticker → {"market": str, "sector": str}
_KRX_STOCK_CACHE_LOADED = False

# KRX 기본 업종명 → 표시용 업종명 매핑
_KRX_SECTOR_DISPLAY = {
    "음식료품":        "소비재",
    "섬유·의복":       "소비재",
    "종이·목재":       "소재",
    "화학":            "소재",
    "의약품":          "건강관리",
    "의료정밀":        "건강관리",
    "비금속광물":      "소재",
    "철강·금속":       "소재",
    "금속":            "소재",
    "기계":            "자본재",
    "전기·전자":       "기술하드웨어와장비",
    "전자부품":        "기술하드웨어와장비",
    "반도체":          "반도체와반도체장비",
    "디스플레이":      "기술하드웨어와장비",
    "IT부품":          "기술하드웨어와장비",
    "운수장비":        "자동차와부품",
    "자동차":          "자동차와부품",
    "유통업":          "소비재",
    "백화점":          "소비재",
    "전기가스업":      "유틸리티",
    "건설업":          "자본재",
    "운수창고업":      "자본재",
    "운송":            "자본재",
    "통신업":          "통신서비스",
    "방송통신":        "통신서비스",
    "금융업":          "금융",
    "은행":            "금융",
    "증권":            "금융",
    "보험":            "금융",
    "서비스업":        "소프트웨어와서비스",
    "IT서비스":        "소프트웨어와서비스",
    "소프트웨어":      "소프트웨어와서비스",
    "오락·문화":       "소프트웨어와서비스",
    "인터넷":          "소프트웨어와서비스",
    "게임":            "소프트웨어와서비스",
    "엔터테인먼트":    "소프트웨어와서비스",
    "2차전지":         "2차전지",
    "배터리":          "2차전지",
    "에너지":          "에너지",
    "정유":            "에너지",
    "우주항공":        "자본재",
    "방위산업":        "자본재",
    "로봇":            "자본재",
    "조선":            "자본재",
}


def _load_krx_stock_cache(api_key: str) -> bool:
    """
    KRX MDCSTAT01901로 KOSPI+KOSDAQ 전종목 시장구분+업종 일괄 조회.
    세션 당 1회만 실행 (캐시 재사용).
    """
    global _KRX_STOCK_CACHE_LOADED
    if _KRX_STOCK_CACHE_LOADED:
        return bool(_KRX_STOCK_CACHE)

    total = 0
    for mkt_id, market_name in [("STK", "KOSPI"), ("KSQ", "KOSDAQ")]:
        try:
            otp = _krx_otp(
                "dbms/MDC/STAT/standard/MDCSTAT01901",
                api_key,
                {"mktId": mkt_id},
            )
            if not otp:
                print(f"  [KRX] {market_name} OTP 실패")
                continue

            rows = _krx_query("MDCSTAT01901", otp, {"mktId": mkt_id})
            count = 0
            for row in rows:
                # 필드명은 대소문자 혼용 대응
                ticker = (row.get("isuSrtCd") or row.get("ISU_SRT_CD") or "").strip()
                sector_raw = (row.get("upjongNm") or row.get("UPJONG_NM") or "").strip()

                if ticker and len(ticker) == 6 and ticker.isdigit():
                    sector_display = _KRX_SECTOR_DISPLAY.get(sector_raw, sector_raw or "기타")
                    _KRX_STOCK_CACHE[ticker] = {
                        "market": market_name,
                        "sector": sector_display,
                    }
                    count += 1
            print(f"  [KRX] {market_name} {count}종목 시장+업종 로드")
            total += count
        except Exception as e:
            print(f"  [KRX] {market_name} 종목정보 로드 실패: {e}")

    _KRX_STOCK_CACHE_LOADED = True
    if total:
        print(f"  [KRX] 전종목 캐시 완료: {len(_KRX_STOCK_CACHE)}개")
    return bool(_KRX_STOCK_CACHE)


# ── KRX 데이터포털 ETF 분배금 조회 ──────────────────────────
# data.krx.co.kr 공개 API — API 키 불필요 (openapi.krx.co.kr 와 다른 포털)

_KRX_DATA_BASE = "https://data.krx.co.kr"

_KRX_DATA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://data.krx.co.kr",
    "Origin": "https://data.krx.co.kr",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


def get_distribution_from_krx(ticker_6: str, years: int = 3) -> list[dict]:
    """
    KRX 정보데이터시스템 (data.krx.co.kr) MDCSTAT04601
    ETF 분배금 지급현황 — API 키 불필요, OTP 2단계 방식
    반환: [{"date": "YYYY.MM.DD", "amount": float|None}, ...] 최신순
    """
    import pandas as _pd
    from io import BytesIO as _BytesIO

    isin = _ticker_to_isin(ticker_6)
    if not isin:
        return []

    end_dt   = datetime.now().strftime("%Y%m%d")
    start_dt = (datetime.now() - timedelta(days=365 * years)).strftime("%Y%m%d")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer":    "https://data.krx.co.kr/",
        "Origin":     "https://data.krx.co.kr",
    }

    try:
        # Step 1: OTP 발급 (generateOTP.cmd)
        otp_r = _req.post(
            "https://data.krx.co.kr/comm/bldAttendant/generateOTP.cmd",
            headers=headers,
            data={
                "locale":       "ko_KR",
                "isuCd":        isin,
                "strtDd":       start_dt,
                "endDd":        end_dt,
                "share":        "1",
                "money":        "1",
                "csvxls_isNo":  "false",
                "name":         "fileDown",
                "url":          "dbms/MDC/STAT/standard/MDCSTAT04601",
            },
            timeout=15,
        )
        otp = otp_r.text.strip()
        if not otp or len(otp) < 10:
            print(f"  [KRX포털] OTP 발급 실패: {otp!r}")
            return []

        # Step 2: CSV 다운로드 (executeForResourceBundle.cmd)
        data_r = _req.post(
            "https://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd",
            headers=headers,
            data={"code": otp},
            timeout=30,
        )

        # CP949 인코딩 CSV 파싱
        try:
            df = _pd.read_csv(_BytesIO(data_r.content), encoding="cp949")
        except Exception:
            df = _pd.read_csv(_BytesIO(data_r.content), encoding="utf-8-sig")

        if df.empty:
            print(f"  [KRX포털] {ticker_6} 데이터 없음")
            return []

        # 컬럼명 확인 (디버깅)
        cols = list(df.columns)

        # 분배기준일 컬럼 찾기
        date_col = next((c for c in cols if "기준일" in c or "분배" in c and "일" in c), None)
        amt_col  = next((c for c in cols if "금액" in c or "분배금" in c), None)

        if not date_col:
            print(f"  [KRX포털] 날짜 컬럼 없음 | 컬럼: {cols}")
            return []

        records = []
        seen = set()
        for _, row in df.iterrows():
            raw_date = str(row.get(date_col, "")).strip()
            if not raw_date or raw_date == "nan":
                continue
            # "2026/04/30" or "2026-04-30" or "20260430" → "2026.04.30"
            raw_date = re.sub(r"[-/]", ".", raw_date.strip())
            if re.match(r"\d{8}$", raw_date.replace(".", "")):
                d = raw_date.replace(".", "")
                raw_date = f"{d[:4]}.{d[4:6]}.{d[6:]}"
            if not re.match(r"\d{4}\.\d{2}\.\d{2}", raw_date):
                continue
            if raw_date in seen:
                continue
            seen.add(raw_date)

            amount = None
            if amt_col:
                try:
                    amount = float(str(row.get(amt_col, "")).replace(",", "").strip())
                except (ValueError, TypeError):
                    pass

            records.append({"date": raw_date, "amount": amount})

        records = sorted(records, key=lambda x: x["date"], reverse=True)
        if records:
            print(f"  [KRX포털] {ticker_6} 분배금 {len(records)}건 수집")
            for rec in records[:3]:
                amt = f"{int(rec['amount'])}원" if rec.get("amount") else "금액미확인"
                print(f"    {rec['date']} {amt}")
        return records

    except Exception as e:
        print(f"  [KRX포털] 오류: {e}")
        return []


def get_distribution_from_naver(ticker_6: str) -> list[dict]:
    """
    Naver Finance ETF 분배금 스크래핑 (KRX 실패 시 백업)
    https://finance.naver.com/item/coinfo.naver?code={ticker}
    반환: [{"date": "YYYY.MM.DD", "amount": float|None}, ...] 최신순
    """
    from bs4 import BeautifulSoup as _BS

    url = f"https://finance.naver.com/item/coinfo.naver?code={ticker_6}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.naver.com/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        r = _req.get(url, headers=headers, timeout=15)
        soup = _BS(r.text, "html.parser")

        # 분배금 테이블 탐색 — 헤더에 "배당" 또는 "분배" 포함 테이블
        records = []
        seen = set()
        for tbl in soup.find_all("table"):
            ths = [th.get_text(strip=True) for th in tbl.find_all("th")]
            has_date = any("기준" in t or "배당일" in t or "분배" in t for t in ths)
            has_amt  = any("배당금" in t or "분배금" in t or "금액" in t for t in ths)
            if not (has_date or has_amt):
                continue

            for tr in tbl.find_all("tr"):
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(tds) < 2:
                    continue
                # 날짜 파싱: "2026.04.30" or "2026-04-30"
                date_str = None
                amount = None
                for cell in tds:
                    m = re.match(r"(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})", cell)
                    if m and not date_str:
                        date_str = f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}"
                    elif re.match(r"[\d,]+$", cell) and date_str and not amount:
                        try:
                            amount = float(cell.replace(",", ""))
                        except ValueError:
                            pass
                if date_str and date_str not in seen:
                    seen.add(date_str)
                    records.append({"date": date_str, "amount": amount})

        records = sorted(records, key=lambda x: x["date"], reverse=True)
        if records:
            print(f"  [Naver] {ticker_6} 분배금 {len(records)}건 수집")
            for rec in records[:3]:
                amt = f"{int(rec['amount'])}원" if rec.get("amount") else "금액미확인"
                print(f"    {rec['date']} {amt}")
        return records

    except Exception as e:
        print(f"  [Naver] 오류: {e}")
        return []


# ── SECTOR_MAP: KRX 캐시 miss 시 fallback ──────────────────
SECTOR_MAP = {
    # 자동차와부품
    "005380": "자동차와부품",   "000270": "자동차와부품",
    "012330": "자동차와부품",   "011210": "자동차와부품",
    "204320": "자동차와부품",   "005850": "자동차와부품",
    # 기술하드웨어
    "009150": "기술하드웨어와장비",   "011070": "기술하드웨어와장비",
    "066570": "기술하드웨어와장비",   "034220": "기술하드웨어와장비",
    "010170": "기술하드웨어와장비",   "007660": "기술하드웨어와장비",
    "032500": "기술하드웨어와장비",   "050890": "기술하드웨어와장비",
    "090460": "기술하드웨어와장비",   "218410": "기술하드웨어와장비",
    # 소프트웨어
    "307950": "소프트웨어와서비스",   "064400": "소프트웨어와서비스",
    "035420": "소프트웨어와서비스",   "036570": "소프트웨어와서비스",
    "047050": "소프트웨어와서비스",   "402340": "소프트웨어와서비스",
    "035900": "소프트웨어와서비스",   "041510": "소프트웨어와서비스",
    "352820": "소프트웨어와서비스",
    # 반도체
    "005930": "반도체와반도체장비",   "000660": "반도체와반도체장비",
    "042700": "반도체와반도체장비",   "058470": "반도체와반도체장비",
    "080220": "반도체와반도체장비",   "073490": "반도체와반도체장비",
    "122990": "반도체와반도체장비",   "077500": "반도체와반도체장비",
    "098460": "반도체와반도체장비",
    # 자본재
    "277810": "자본재",   "454910": "자본재",   "108490": "자본재",
    "058610": "자본재",   "042660": "자본재",   "047810": "자본재",
    "012450": "자본재",   "034020": "자본재",   "009540": "자본재",
    "000720": "자본재",   "006360": "자본재",
    # 에너지/소재
    "010950": "에너지",   "096770": "에너지",
    "010130": "소재",     "051910": "소재",   "011170": "소재",
    "003670": "소재",
    # 2차전지
    "006400": "2차전지",  "373220": "2차전지",
    "247540": "2차전지",  "086520": "2차전지",
    # 금융
    "105560": "금융",  "055550": "금융",  "086790": "금융",
    "138930": "금융",  "316140": "금융",  "086280": "금융",
    "000810": "금융",  "032830": "금융",  "024110": "금융",
    # 건강관리
    "207940": "건강관리",  "068270": "건강관리",  "128940": "건강관리",
    "000100": "건강관리",  "069620": "건강관리",  "185750": "건강관리",
    "009290": "건강관리",
    # 통신/유틸
    "017670": "통신서비스",  "030200": "통신서비스",  "032640": "통신서비스",
    "015760": "유틸리티",    "036460": "유틸리티",
    # 소비재 / 유통
    "035000": "소비재",  "051900": "소비재",
    "028260": "소비재",  # 삼성물산 (건설·유통·상사 복합)
}

# ── MARKET_MAP: KRX 캐시·yfinance 실패 시 최종 fallback ─────
# KOSPI 대형주 하드코딩 (SECTOR_MAP 전체 + 추가 대형주)
# ※ KOSDAQ 종목은 별도 관리, 미포함 = 기본적으로 KOSPI 우선 시도
MARKET_MAP: dict[str, str] = {
    # SECTOR_MAP 전체 = KOSPI
    **{t: "KOSPI" for t in SECTOR_MAP},
    # 추가 KOSPI 대형주
    "000020": "KOSPI",  # 동화약품
    "000040": "KOSPI",  # KR모터스
    "000150": "KOSPI",  # 두산
    "000210": "KOSPI",  # 대림산업
    "000880": "KOSPI",  # 한화
    "001040": "KOSPI",  # CJ
    "001300": "KOSPI",  # 이마트
    "003490": "KOSPI",  # 대한항공
    "003550": "KOSPI",  # LG
    "004020": "KOSPI",  # 현대제철
    "004170": "KOSPI",  # 신세계
    "005490": "KOSPI",  # POSCO홀딩스
    "006800": "KOSPI",  # 미래에셋증권
    "010620": "KOSPI",  # 현대미포조선
    "011790": "KOSPI",  # SKC
    "012750": "KOSPI",  # 에스원
    "015020": "KOSPI",  # 이엔코퍼레이션
    "016360": "KOSPI",  # 삼성증권
    "017800": "KOSPI",  # 현대엘리베이터
    "018260": "KOSPI",  # 삼성에스디에스
    "020150": "KOSPI",  # 롯데에너지머티리얼즈
    "021240": "KOSPI",  # 코웨이
    "023530": "KOSPI",  # 롯데쇼핑
    "024840": "KOSPI",  # KBI동국실업
    "028050": "KOSPI",  # 삼성엔지니어링
    "028260": "KOSPI",  # 삼성물산
    "030000": "KOSPI",  # 제일기획
    "032640": "KOSPI",  # LG유플러스
    "033780": "KOSPI",  # KT&G
    "034020": "KOSPI",  # 두산에너빌리티
    "034730": "KOSPI",  # SK
    "036460": "KOSPI",  # 한국가스공사
    "036570": "KOSPI",  # 엔씨소프트
    "042700": "KOSPI",  # 한미반도체
    "047050": "KOSPI",  # 포스코인터내셔널
    "051600": "KOSPI",  # 한전KPS
    "055550": "KOSPI",  # 신한지주
    "057050": "KOSPI",  # 현대홈쇼핑
    "060980": "KOSPI",  # 한화솔루션
    "066570": "KOSPI",  # LG전자
    "071050": "KOSPI",  # 한국금융지주
    "078930": "KOSPI",  # GS
    "086280": "KOSPI",  # 현대글로비스
    "088350": "KOSPI",  # 한화생명
    "096770": "KOSPI",  # SK이노베이션
    "105560": "KOSPI",  # KB금융
    "120110": "KOSPI",  # 코오롱인더
    "138040": "KOSPI",  # 메리츠금융지주
    "139480": "KOSPI",  # 이마트
    "161390": "KOSPI",  # 한국타이어앤테크놀로지
    "180640": "KOSPI",  # 한진칼
    "192400": "KOSPI",  # 쿠쿠홀딩스
    "207940": "KOSPI",  # 삼성바이오로직스
    "267250": "KOSPI",  # HD현대
    "272210": "KOSPI",  # 한화시스템
    "282330": "KOSPI",  # BGF리테일
    "294870": "KOSPI",  # HDC현대산업개발
    "316140": "KOSPI",  # 우리금융지주
    "329180": "KOSPI",  # HD현대중공업
    "352820": "KOSPI",  # 하이브
    "373220": "KOSPI",  # LG에너지솔루션
    "402340": "KOSPI",  # 삼성SDS
    "003240": "KOSPI",  # 태광산업
    # KOSDAQ 대형주
    "086520": "KOSDAQ",  # 에코프로
    "247540": "KOSDAQ",  # 에코프로비엠
    "064400": "KOSDAQ",  # 위메이드
    "041510": "KOSDAQ",  # 에스엠
    "035900": "KOSDAQ",  # JYP엔터
    "122990": "KOSDAQ",  # 와이솔
    "077500": "KOSDAQ",  # 유니퀘스트
    "098460": "KOSDAQ",  # 고영
    "032500": "KOSDAQ",  # 케이엠더블유
    "050890": "KOSDAQ",  # 쏠리드
    "073490": "KOSDAQ",  # 이수페타시스
    "080220": "KOSDAQ",  # 제주반도체
    "058470": "KOSDAQ",  # 리노공업
    "454910": "KOSDAQ",  # 레인보우로보틱스
}


# ── KRX 상장일 캐시 ──────────────────────────────────────────
_LISTING_CACHE: dict[str, str] = {}  # ticker → "YYYY.MM.DD"


def get_listing_date_from_krx(ticker_6: str, api_key: str) -> str:
    """KRX MDCSTAT04101 → ETF 상장일(listDd) 조회"""
    if ticker_6 in _LISTING_CACHE:
        return _LISTING_CACHE[ticker_6]

    isin = _ticker_to_isin(ticker_6)
    if not isin:
        return ""

    otp = _krx_otp(
        "dbms/MDC/STAT/standard/MDCSTAT04101",
        api_key,
        {"isuCd": isin},
    )
    if not otp:
        return ""

    rows = _krx_query("MDCSTAT04101", otp)
    for row in rows:
        raw = (row.get("listDd") or row.get("LIST_DD") or "").strip()
        if raw and len(raw) == 8:
            date_str = f"{raw[:4]}.{raw[4:6]}.{raw[6:]}"
            _LISTING_CACHE[ticker_6] = date_str
            print(f"  [KRX] {ticker_6} 상장일={date_str}")
            return date_str
    return ""


def _ticker_to_isin(ticker_6: str) -> str:
    """6자리 티커 → ISIN (KRX Luhn 체크섬)"""
    if not ticker_6 or len(ticker_6) != 6:
        return ""
    prefix = f"KR7{ticker_6}00"
    num_str = ""
    for c in prefix:
        num_str += c if c.isdigit() else str(ord(c) - ord('A') + 10)
    digits = [int(d) for d in num_str]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return prefix + str((10 - total % 10) % 10)


# ── KRXCollector 클래스 ──────────────────────────────────────
class KRXCollector:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def ensure_stock_cache(self):
        """전종목 캐시 1회 로드 (이미 로드됐으면 바로 반환)"""
        if self.api_key:
            _load_krx_stock_cache(self.api_key)

    def get_stock_market(self, ticker_6: str) -> str:
        """KOSPI/KOSDAQ 판별: KRX 캐시 → MARKET_MAP → yfinance → UNKNOWN"""
        # 1. KRX 전종목 캐시
        info = _KRX_STOCK_CACHE.get(ticker_6)
        if info:
            return info["market"]
        # 2. MARKET_MAP 하드코딩 (KRX API 차단 시 확실한 fallback)
        if ticker_6 in MARKET_MAP:
            return MARKET_MAP[ticker_6]
        # 3. yfinance
        if YF_OK:
            return self._yf_market(ticker_6)
        return "UNKNOWN"

    def _yf_market(self, ticker_6: str) -> str:
        for suffix, market in [(".KS", "KOSPI"), (".KQ", "KOSDAQ")]:
            try:
                t = yf.Ticker(f"{ticker_6}{suffix}")
                price = getattr(t.fast_info, "last_price", None)
                if price and price > 0:
                    return market
            except Exception:
                pass
        return "UNKNOWN"

    def get_sector(self, ticker_6: str) -> str:
        """업종 조회: KRX 캐시 → SECTOR_MAP → 기타"""
        info = _KRX_STOCK_CACHE.get(ticker_6)
        if info and info.get("sector") and info["sector"] != "기타":
            return info["sector"]
        return SECTOR_MAP.get(ticker_6, "기타")

    def enrich_holdings(self, holdings: list[dict]) -> list[dict]:
        """보유종목에 market, sector 정보 추가"""
        self.ensure_stock_cache()   # 첫 ETF 처리 시 1회 로드
        for h in holdings:
            ticker = h.get("ticker", "")
            if ticker:
                h["market"] = self.get_stock_market(ticker)
                h["sector"] = self.get_sector(ticker)
            else:
                h["market"] = self._guess_market_by_name(h.get("name", ""))
                h["sector"] = self._guess_sector_by_name(h.get("name", ""))
        return holdings

    def _guess_market_by_name(self, name: str) -> str:
        kosdaq_names = {"레인보우로보틱스", "로보티즈", "에스피지", "고영",
                        "리노공업", "제주반도체", "쏠리드", "RFHIC", "케이엠더블유"}
        if name in kosdaq_names:
            return "KOSDAQ"
        kospi_kw = ["현대차", "현대모비스", "기아", "LG이노텍", "LG씨엔에스",
                    "현대오토에버", "두산로보틱스", "에스엘", "HL만도", "현대위아",
                    "삼성전자", "SK하이닉스", "삼성전기", "이수페타시스",
                    "POSCO", "LG전자", "카카오", "NAVER", "SK스퀘어",
                    "셀트리온", "삼성바이오", "한화", "KB금융", "신한",
                    "대한광통신"]
        for kw in kospi_kw:
            if kw in name:
                return "KOSPI"
        return "UNKNOWN"

    def _guess_sector_by_name(self, name: str) -> str:
        mappings = [
            (["현대차","기아","모비스","위아","만도","에스엘"],          "자동차와부품"),
            (["삼성전기","이노텍","씨엔에스","오토에버","이수페타시스",
              "대한광통신","케이엠더블유","쏠리드","RFHIC"],             "기술하드웨어와장비"),
            (["SK스퀘어","NAVER","카카오","하이브","JYP","SM엔터"],      "소프트웨어와서비스"),
            (["삼성전자","하이닉스","리노공업","제주반도체"],              "반도체와반도체장비"),
            (["레인보우로보틱스","두산로보틱스","로보티즈","에스피지",
              "한화에어로","한화오션","조선해양","항공우주"],              "자본재"),
            (["삼성바이오","셀트리온","한미약품","유한양행"],              "건강관리"),
            (["KB금융","신한","하나금융","우리금융","기업은행"],            "금융"),
            (["삼성SDI","LG에너지","에코프로"],                         "2차전지"),
        ]
        for kws, sector in mappings:
            if any(kw in name for kw in kws):
                return sector
        return "기타"

    def get_index_data(self, fromdate: str, todate: str, market: str) -> list[dict]:
        if not YF_OK:
            return []
        yf_ticker = "^KS11" if market == "KOSPI" else "^KQ11"
        def fmt(d): return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        try:
            import pandas as _pd
            end_dt = datetime.strptime(todate, "%Y%m%d") + timedelta(days=2)
            df = yf.download(
                yf_ticker,
                start=fmt(fromdate),
                end=end_dt.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                return []
            close = df["Close"]
            if hasattr(close, "squeeze"):
                close = close.squeeze()
            result = []
            for dt, val in close.items():
                if hasattr(dt, "strftime"):
                    d = dt.strftime("%Y%m%d")
                else:
                    d = str(dt)[:10].replace("-", "")
                try:
                    result.append({"date": d, "close": float(val)})
                except (TypeError, ValueError):
                    pass
            return result
        except Exception as e:
            print(f"  [yfinance] {yf_ticker} 오류: {e}")
            return []
    def determine_bm(self, holdings: list[dict]) -> str:
        """보유종목 시장 비중으로 KOSPI/KOSDAQ BM 결정"""
        if not holdings:
            return "KOSPI"
        kospi_w = sum(h.get("weight", 0) for h in holdings if h.get("market") == "KOSPI")
        kosdaq_w = sum(h.get("weight", 0) for h in holdings if h.get("market") == "KOSDAQ")
        return "KOSPI" if kospi_w >= kosdaq_w else "KOSDAQ"

    @staticmethod
    def aggregate_sectors(holdings: list[dict]) -> list[dict]:
        """보유종목 업종별 비중 집계"""
        sector_map: dict[str, float] = {}
        for h in holdings:
            sector = h.get("sector", "기타") or "기타"
            weight = h.get("weight", 0) or 0
            sector_map[sector] = sector_map.get(sector, 0) + weight
        result = [
            {"sector": s, "weight": round(w, 2)}
            for s, w in sorted(sector_map.items(), key=lambda x: -x[1])
        ]
        return result
