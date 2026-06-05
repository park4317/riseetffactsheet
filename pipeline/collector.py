# ============================================================
#  RISE ETF 데이터 수집기 (RISE 홈페이지 기반)
# ============================================================

import re
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from config import RISE_BASE_URL, HEADERS, NAV_HISTORY_DAYS
from krx_collector import KRXCollector


def _fetch_df(session, url: str) -> pd.DataFrame | None:
    """HTML-as-Excel 엔드포인트 → DataFrame (pd.read_html 우선)"""
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    try:
        tables = pd.read_html(BytesIO(resp.content), encoding="utf-8")
        return tables[0] if tables else None
    except Exception:
        return None


class RISECollector:
    def __init__(self, site_id: str):
        self.site_id = site_id
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.krx = KRXCollector()

    # ─────────────────────────────────────
    #  1. NAV·가격·거래량 이력
    #
    #  ⚠️ Excel1(거래정보)의 NAV 컬럼은 T+1 리포팅 구조
    #     (05.13 행에 05.12 NAV가 기록) → NAV/price 괴리율 계산 오류 발생
    #
    #  수정: Excel2(수익률)에서 날짜별 정확한 NAV+시장가격 수집
    #        Excel1에서는 거래량만 추출해 병합
    # ─────────────────────────────────────
    def get_nav_history(self) -> list[dict]:
        end   = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=NAV_HISTORY_DAYS)).strftime("%Y-%m-%d")

        # ① Excel2: 날짜별 정확한 NAV + 시장가격
        url2 = (f"{RISE_BASE_URL}/prod/finder/productViewTabExcel2"
                f"?searchTargetId={self.site_id}"
                f"&searchStartDate={start}&searchEndDate={end}")
        # ② Excel1: 거래량 (NAV 컬럼은 무시)
        url1 = f"{RISE_BASE_URL}/prod/finder/productViewTabExcel1?searchTargetId={self.site_id}"
        try:
            df2 = _fetch_df(self.session, url2)
            df1 = _fetch_df(self.session, url1)
            return self._merge_nav(df2, df1)
        except Exception as e:
            print(f"  [NAV 오류] {e}")
            return []

    def _merge_nav(self, df2, df1) -> list[dict]:
        """Excel2(NAV·가격)와 Excel1(거래량)을 날짜 기준으로 병합"""
        def safe_float(v):
            try: return float(v)
            except: return None
        def safe_int(v):
            try: return int(float(v))
            except: return None

        records: dict[str, dict] = {}

        # ── Excel2 파싱 (기준: 수익률 파일, 최신→오래된 순 정렬) ──
        if df2 is not None:
            h2 = df2.iloc[4].tolist()
            c_date  = next((i for i,v in enumerate(h2) if str(v)=="일자"), 1)
            c_nav   = next((i for i,v in enumerate(h2) if "기준가격" in str(v)), 2)
            c_price = next((i for i,v in enumerate(h2) if "시장가격" in str(v)), 4)

            for _, row in df2.iloc[5:].iterrows():
                d = str(row.iloc[c_date]).strip()
                if not re.match(r'\d{4}\.\d{2}\.\d{2}', d):
                    continue
                nav_f = safe_float(row.iloc[c_nav])
                if nav_f is None or nav_f < 1000:
                    continue
                records[d] = {
                    "date":  d,
                    "nav":   round(nav_f, 2),
                    "price": safe_int(row.iloc[c_price]) if c_price < len(row) else None,
                    "volume": None,
                }

        # ── Excel1 파싱: 거래량만 추출 (NAV 컬럼 무시) ──
        if df1 is not None:
            h1 = df1.iloc[4].tolist()
            c_date1 = next((i for i,v in enumerate(h1) if str(v)=="일자"), 1)
            c_vol   = next((i for i,v in enumerate(h1) if "거래량" in str(v)), 5)
            c_px1   = next((i for i,v in enumerate(h1) if "시장가격" in str(v)), 4)

            for _, row in df1.iloc[5:].iterrows():
                d = str(row.iloc[c_date1]).strip()
                if not re.match(r'\d{4}\.\d{2}\.\d{2}', d):
                    continue
                vol  = safe_int(row.iloc[c_vol])
                px1  = safe_int(row.iloc[c_px1])
                if d in records:
                    records[d]["volume"] = vol
                    # Excel2에 시장가격이 없으면 Excel1로 보완
                    if records[d]["price"] is None and px1:
                        records[d]["price"] = px1

        return sorted(records.values(), key=lambda x: x["date"])

    # ─────────────────────────────────────
    #  2. 기간별 수익률
    #     producProfitTabExcel2
    #     행5=헤더, 행6=NAV 수익률
    # ─────────────────────────────────────
    def get_performance(self) -> dict:
        url = f"{RISE_BASE_URL}/prod/finder/producProfitTabExcel2?searchTargetId={self.site_id}"
        perf = {k: None for k in ("1m","3m","6m","1y","3y","ytd","since_listing")}
        try:
            df = _fetch_df(self.session, url)
            if df is None: return perf
            header  = df.iloc[5].tolist()
            nav_row = df.iloc[6].tolist()
            key_map = {"1개월":"1m","3개월":"3m","6개월":"6m","1년":"1y",
                       "3년":"3y","연초이후":"ytd","상장이후":"since_listing"}
            for i, col_name in enumerate(header):
                k = key_map.get(str(col_name).strip())
                if k:
                    try: perf[k] = round(float(nav_row[i]), 2)
                    except: pass
        except Exception as e:
            print(f"  [수익률 오류] {e}")
        return perf

    # ─────────────────────────────────────
    #  3. 일별 수익률 (테이블용, 전일 종가까지)
    #     productViewTabExcel2
    #     컬럼: 일자, ETF기준가격, 증감(%), 시장가격, 증감(%), 과표기준가
    # ─────────────────────────────────────
    def get_daily_returns(self, rows: int = 8) -> list[dict]:
        end   = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = (
            f"{RISE_BASE_URL}/prod/finder/productViewTabExcel2"
            f"?searchTargetId={self.site_id}"
            f"&searchStartDate={start}&searchEndDate={end}"
        )
        try:
            df = _fetch_df(self.session, url)
            if df is None: return []
            header   = df.iloc[4].tolist()
            col_date = next((i for i, v in enumerate(header) if str(v) == "일자"), 1)
            col_nav  = next((i for i, v in enumerate(header) if "기준가격" in str(v)), 2)
            col_ret  = next((i for i, v in enumerate(header) if "증감" in str(v)), 3)

            records = []
            for _, row in df.iloc[5:].iterrows():
                date_v = str(row.iloc[col_date]).strip()
                if not re.match(r'\d{4}\.\d{2}\.\d{2}', date_v):
                    continue
                try:
                    nav_f = float(row.iloc[col_nav])
                    ret_f = float(row.iloc[col_ret])
                except (ValueError, TypeError):
                    continue
                # 당일(price=None인 날) 포함, 단 종가=0인 행 제외
                records.append({"date": date_v, "nav": round(nav_f, 2),
                                 "return_pct": round(ret_f, 2)})

            # 최신순 정렬 후 전일 종가까지 (당일 = 가장 최근 날짜 제외)
            records = sorted(records, key=lambda x: x["date"], reverse=True)
            if records:
                records = records[1:]   # 당일 제외
            return records[:rows]
        except Exception as e:
            print(f"  [일별수익률 오류] {e}")
            return []

    # ─────────────────────────────────────
    #  4. 구성종목 TOP10 + 티커코드
    # ─────────────────────────────────────
    def get_holdings_and_meta(self) -> tuple[list[dict], dict]:
        """구성종목 TOP10 + 페이지에서 추출 가능한 메타(AUM 등) 동시 반환"""
        url = f"{RISE_BASE_URL}/prod/finderDetail/{self.site_id}"
        try:
            resp = self.session.get(url, timeout=20)
            soup = BeautifulSoup(resp.content, "lxml")
            holdings = self._parse_holdings(soup)
            meta     = self._parse_page_meta(soup)
            return holdings, meta
        except Exception as e:
            print(f"  [구성종목/메타 오류] {e}")
            return [], {}

    def _parse_page_meta(self, soup: BeautifulSoup) -> dict:
        """상세 페이지에서 AUM 등 추가 메타 추출"""
        meta = {}
        text = soup.get_text(" ")

        # 순자산 규모 (억원) — "5,647억" 또는 숫자
        m = re.search(r'순\s*자\s*산\s*규모[^0-9]*([0-9,]+)', text)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                val = int(raw)
                if val > 1_000_000:      # 원 단위 → 억원 변환
                    meta["aum_display"] = f"{val // 100_000_000:,}"
                elif val > 100:          # 이미 억원 단위
                    meta["aum_display"] = f"{val:,}"
            except ValueError:
                pass
        return meta

    def _parse_holdings(self, soup: BeautifulSoup) -> list[dict]:
        holdings = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) < 3:
                    continue
                if not re.match(r'^\d+$', cells[0]):
                    continue

                # 비중(%) 컬럼: [\d.]+ 패턴인 셀 중 마지막
                weight_val = None
                for cell in reversed(cells[1:]):
                    if re.match(r'^\d{1,3}\.\d{1,2}$', cell):
                        try:
                            w = float(cell)
                            if 0 < w < 100:
                                weight_val = w
                                break
                        except ValueError:
                            pass
                if weight_val is None:
                    continue

                # 티커코드 추출 (KR7XXXXXXX001 형식)
                ticker = ""
                for cell in cells:
                    m = re.match(r'KR7(\d{6})', cell)
                    if m:
                        ticker = m.group(1)
                        break

                name = cells[1] if len(cells) > 1 else ""
                if "현금" in name:
                    continue

                holdings.append({
                    "rank":   int(cells[0]),
                    "name":   name,
                    "ticker": ticker,
                    "weight": weight_val,
                })

        holdings = sorted(holdings, key=lambda x: x["rank"])[:10]
        return holdings

    # ─────────────────────────────────────
    #  5. 20일 평균 거래량 계산
    # ─────────────────────────────────────
    @staticmethod
    def calc_avg_volume(nav_history: list[dict], days: int = 20) -> int | None:
        """최근 N 영업일 평균 거래량 (거래량 있는 날만)"""
        vols = [r["volume"] for r in nav_history if r.get("volume")]
        recent = vols[-days:]
        if not recent:
            return None
        return int(sum(recent) / len(recent))

    # ─────────────────────────────────────
    #  6. 전체 수집 (올인원)
    # ─────────────────────────────────────
    def collect_all(self) -> dict:
        print(f"  [수집 시작] site_id={self.site_id}")

        nav               = self.get_nav_history()
        perf              = self.get_performance()
        daily             = self.get_daily_returns()
        holdings, page_meta = self.get_holdings_and_meta()

        # 구성종목에 시장구분·업종 추가
        holdings = self.krx.enrich_holdings(holdings)

        # BM 결정 + 지수 데이터 수집
        bm_name = self.krx.determine_bm(holdings)
        listing_date = nav[0]["date"].replace(".", "") if nav else \
                       (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        today = datetime.now().strftime("%Y%m%d")
        bm_data = self.krx.get_index_data(listing_date, today, bm_name)

        # 업종별 비중
        sector_data = KRXCollector.aggregate_sectors(holdings)

        # 평균 거래량
        avg_vol_20 = self.calc_avg_volume(nav, days=20)

        # 당일 데이터 제외한 최신 기록
        tradeable = [r for r in nav if r.get("price")]
        latest    = tradeable[-1] if tradeable else {}

        # 표시 수익률: 1개월 우선, 없으면 상장이후
        if perf.get("1m") is not None:
            display_return       = perf["1m"]
            display_return_label = "1개월"
        else:
            display_return       = perf.get("since_listing")
            display_return_label = "상장이후"

        print(
            f"  NAV {len(nav)}일 | BM={bm_name} {len(bm_data)}일 | "
            f"구성종목 {len(holdings)}개 | 수익률({display_return_label}) {display_return}%"
        )

        return {
            "collected_at":         datetime.now().strftime("%Y.%m.%d %H:%M"),
            "nav_history":          nav,
            "bm_history":           bm_data,
            "bm_name":              bm_name,
            "performance":          perf,
            "display_return":       display_return,
            "display_return_label": display_return_label,
            "daily_returns":        daily,
            "holdings":             holdings,
            "sector_data":          sector_data,
            "latest":               latest,
            "avg_volume_20d":       avg_vol_20,
            "aum_raw":              page_meta.get("aum_display"),  # 억원 문자열
        }
