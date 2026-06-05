# ============================================================
#  KRX 데이터 수집기 (yfinance + 정적 매핑 기반)
#
#  pykrx 최신 버전이 KRX 로그인을 요구하므로
#  - 지수 데이터: yfinance (^KS11 / ^KQ11)
#  - 시장구분/업종: 정적 매핑 테이블 (ETF 주요 편입 종목 커버)
# ============================================================

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False
    print("[경고] yfinance 미설치 → pip install yfinance")

from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────
#  시장 구분 정적 테이블 (6자리 종목코드 기준)
#  국내주식형 ETF 주요 편입 종목 커버
# ─────────────────────────────────────────────────────────────
KOSPI_STOCKS = {
    # 자동차·부품
    "005380","000270","012330","011210","204320","005850","009150","010950",
    # 반도체
    "005930","000660","042700","023590","009830","048260","058470",
    # IT·전자
    "011070","066570","034220","003550","051900","051910","009830",
    # IT서비스
    "307950","064400","035420","036570","047050",
    # 에너지·화학
    "010950","011170","051910","096770","017670",
    # 금융
    "105560","055550","086790","316140","138930","086280","000810","032830",
    "139130","024110","000240","006400",
    # 건강관리·바이오
    "207940","068270","128940","069620","185750","009290",
    # 방산·산업재
    "012450","047810","006360","042660","034020","011790","009540","000720",
    "000880","003490","003240","010140","017800","018260","021240","025900",
    "028050","034730","036460","036580","039490","047050","060980","069960",
    "078935","082920","085620","086280","088350","091810","095720","097950",
    "105560","112610","115390","120030","130550","139480","143210","145270",
    "148150","151800","161390","165720","170900","175330","178920","180640",
    "192820","199800","210540","214430","214450","251270","263720","267250",
    "271560","272210","282690","283450","285130","288490","290270","294870",
    "298040","298050","316140","323410","326030","329180","334890","336260",
    "337140","339770","339830","347860","348210","352820","357120","361610",
    "363280","365550","368770","377300","377440","383220","384030","402340",
    "405640","432320","443060","448730","950130",
    # 로보틱스 (KOSPI 상장)
    "454910",  # 두산로보틱스
}

KOSDAQ_STOCKS = {
    # AI·반도체
    "086520","091990","196170","035900","086900","178600","073010","039030",
    "078860","095340","095570","096530","098460","099190","102940","103140",
    "104480","112040","119850","122870","131030","145020","155900","183300",
    "222080","236340","241590","263020","268280","293490","302440","317850",
    # 로보틱스·자동화
    "277810",  # 레인보우로보틱스
    "108490",  # 로보티즈
    "058610",  # 에스피지
    "335890",  # 비올
    "322000","330350","357780","368770","393210","393560","402030","403870",
    "404990","421020","432690","950220",
    # 바이오
    "068760","039200","041960","048820","060300","068760","078520","086820",
    "096770","115180","138360","145020","155900","175250","187660","214150",
    "214980","263750","294870","298000","323280","326230","365340","377440",
}

# ─────────────────────────────────────────────────────────────
#  KRX WICS 업종 매핑 (주요 편입 종목 기준)
# ─────────────────────────────────────────────────────────────
SECTOR_MAP = {
    # 자동차와부품
    "005380": "자동차와부품",   # 현대차
    "000270": "자동차와부품",   # 기아
    "012330": "자동차와부품",   # 현대모비스
    "011210": "자동차와부품",   # 현대위아
    "204320": "자동차와부품",   # HL만도
    "005850": "자동차와부품",   # 에스엘
    # 기술하드웨어
    "011070": "기술하드웨어와장비",  # LG이노텍
    "066570": "기술하드웨어와장비",  # LG전자
    # 소프트웨어·IT서비스
    "307950": "소프트웨어와서비스",  # 현대오토에버
    "064400": "소프트웨어와서비스",  # LG씨엔에스
    "035420": "소프트웨어와서비스",  # NAVER
    "036570": "소프트웨어와서비스",  # NCsoft
    "047050": "소프트웨어와서비스",  # 포스코ICT
    # 반도체
    "005930": "반도체와반도체장비",  # 삼성전자
    "000660": "반도체와반도체장비",  # SK하이닉스
    "098460": "반도체와반도체장비",  # 고영
    "042700": "반도체와반도체장비",  # 한미반도체
    # 자본재 (산업재)
    "277810": "자본재",   # 레인보우로보틱스
    "454910": "자본재",   # 두산로보틱스
    "108490": "자본재",   # 로보티즈
    "058610": "자본재",   # 에스피지
    "042660": "자본재",   # 한화오션
    "047810": "자본재",   # 한국항공우주
    "012450": "자본재",   # 한화에어로스페이스
    "034020": "자본재",   # 두산에너빌리티
    "006360": "자본재",   # GS건설
    # 에너지
    "010950": "에너지",   # S-Oil
    "096770": "에너지",   # SK이노베이션
    # 소재
    "010130": "소재",     # 고려아연
    "051910": "소재",     # LG화학
    "051900": "소재",     # LG생활건강
    "011170": "소재",     # 롯데케미칼
    # 금융
    "105560": "금융",     # KB금융
    "055550": "금융",     # 신한지주
    "086790": "금융",     # 하나금융지주
    "138930": "금융",     # BNK금융지주
    "316140": "금융",     # 우리금융지주
    # 건강관리
    "207940": "건강관리",  # 삼성바이오로직스
    "068270": "건강관리",  # 셀트리온
    "128940": "건강관리",  # 한미약품
    # 통신서비스
    "017670": "통신서비스",  # SK텔레콤
    "030200": "통신서비스",  # KT
    "032640": "통신서비스",  # LG유플러스
    # 유틸리티
    "015760": "유틸리티",  # 한국전력
}


class KRXCollector:
    """
    KRX 데이터 수집기
    - 시장구분/업종: 정적 테이블 기반 (빠르고 안정적)
    - 지수 데이터: yfinance (^KS11 / ^KQ11)
    """

    # ── 시장 구분 ──────────────────────────────────────────
    def get_stock_market(self, ticker_6: str, date: str = None) -> str:
        """6자리 종목코드 → 'KOSPI' / 'KOSDAQ' / 'UNKNOWN'"""
        if ticker_6 in KOSPI_STOCKS:  return "KOSPI"
        if ticker_6 in KOSDAQ_STOCKS: return "KOSDAQ"
        # 정적 테이블에 없으면 yfinance로 확인
        if YF_OK:
            return self._yf_market(ticker_6)
        return "UNKNOWN"

    def _yf_market(self, ticker_6: str) -> str:
        """yfinance로 시장 구분 (폴백)"""
        for suffix, market in [(".KS", "KOSPI"), (".KQ", "KOSDAQ")]:
            try:
                t = yf.Ticker(f"{ticker_6}{suffix}")
                info = t.fast_info
                price = getattr(info, "last_price", None)
                if price and price > 0:
                    return market
            except Exception:
                pass
        return "UNKNOWN"

    # ── 업종 ───────────────────────────────────────────────
    def get_sector(self, ticker_6: str, market: str = None, date: str = None) -> str:
        """KRX WICS 업종명 반환"""
        return SECTOR_MAP.get(ticker_6, "기타")

    # ── KOSPI/KOSDAQ 지수 (yfinance) ──────────────────────
    def get_index_data(self, fromdate: str, todate: str, market: str) -> list[dict]:
        """
        KOSPI 또는 KOSDAQ 지수 일별 종가 반환
        fromdate/todate: "YYYYMMDD" 형식
        반환: [{"date": "2026.05.12", "close": 2850.12}, ...]
        """
        if not YF_OK:
            return []
        yf_ticker = "^KS11" if market == "KOSPI" else "^KQ11"
        # YYYYMMDD → YYYY-MM-DD
        def fmt(d): return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        try:
            # end 날짜를 +2일 해서 최신 데이터 누락 방지 (yfinance end exclusive)
            from datetime import datetime as _dt, timedelta as _td
            end_dt = _dt.strptime(todate, "%Y%m%d") + _td(days=2)
            df = yf.download(yf_ticker, start=fmt(fromdate), end=end_dt.strftime("%Y-%m-%d"),
                             progress=False, auto_adjust=True)
            if df is None or df.empty:
                return []
            records = []
            for idx, row in df.iterrows():
                close = row["Close"]
                # multi-level columns 처리
                if hasattr(close, "iloc"):
                    close = float(close.iloc[0])
                else:
                    close = float(close)
                records.append({"date": idx.strftime("%Y.%m.%d"), "close": close})
            print(f"  BM({market}) {len(records)}일치 수집")
            return records
        except Exception as e:
            print(f"  [지수 데이터 오류] {market}: {e}")
            return []

    # ── BM 자동 결정 ───────────────────────────────────────
    def determine_bm(self, holdings: list[dict]) -> str:
        """구성종목 시장 비중으로 KOSPI/KOSDAQ 자동 선택"""
        kospi_w  = sum(h.get("weight", 0) for h in holdings if h.get("market") == "KOSPI")
        kosdaq_w = sum(h.get("weight", 0) for h in holdings if h.get("market") == "KOSDAQ")
        return "KOSPI" if kospi_w >= kosdaq_w else "KOSDAQ"

    # ── 구성종목에 시장·업종 일괄 추가 ────────────────────
    def enrich_holdings(self, holdings: list[dict], date: str = None) -> list[dict]:
        """holdings 리스트에 market, sector 필드 추가"""
        for h in holdings:
            ticker = h.get("ticker", "")
            if ticker:
                h["market"] = self.get_stock_market(ticker)
                h["sector"] = self.get_sector(ticker)
            else:
                # ticker가 없으면 종목명으로 추론
                h["market"] = self._guess_market_by_name(h.get("name", ""))
                h["sector"] = self._guess_sector_by_name(h.get("name", ""))
        return holdings

    def _guess_market_by_name(self, name: str) -> str:
        """종목명 기반 시장 추론 (ticker 없을 때 폴백)"""
        # KOSDAQ 종목 (확실한 것만)
        kosdaq_exact = {"레인보우로보틱스", "로보티즈", "에스피지", "고영"}
        if name in kosdaq_exact:
            return "KOSDAQ"
        # 나머지 한국 대형주 → 대부분 KOSPI
        kospi_keywords = ["현대차", "현대모비스", "기아", "LG이노텍", "LG씨엔에스",
                          "현대오토에버", "두산로보틱스", "에스엘", "HL만도", "현대위아",
                          "삼성전자", "SK하이닉스", "POSCO", "LG전자", "카카오", "NAVER",
                          "셀트리온", "삼성바이오", "한화", "KB금융", "신한"]
        for kw in kospi_keywords:
            if kw in name:
                return "KOSPI"
        return "UNKNOWN"

    def _guess_sector_by_name(self, name: str) -> str:
        """종목명 기반 업종 추론"""
        mappings = [
            (["현대차","기아","모비스","위아","만도","에스엘"],      "자동차와부품"),
            (["이노텍","씨엔에스","오토에버"],                      "정보기술"),
            (["레인보우로보틱스","두산로보틱스","로보티즈","에스피지","고영"], "자본재"),
            (["삼성전자","하이닉스"],                               "반도체와반도체장비"),
            (["삼성바이오","셀트리온","한미약품"],                   "건강관리"),
            (["KB금융","신한","하나금융","우리금융"],                 "금융"),
        ]
        for keywords, sector in mappings:
            if any(kw in name for kw in keywords):
                return sector
        return "기타"

    # ── 업종별 비중 집계 ───────────────────────────────────
    @staticmethod
    def aggregate_sectors(holdings: list[dict]) -> list[dict]:
        """holdings → 업종별 비중 합산 (내림차순)"""
        acc: dict[str, float] = {}
        for h in holdings:
            s = h.get("sector", "기타")
            acc[s] = acc.get(s, 0) + h.get("weight", 0)
        return sorted(
            [{"sector": k, "weight": round(v, 2)} for k, v in acc.items()],
            key=lambda x: x["weight"], reverse=True,
        )
