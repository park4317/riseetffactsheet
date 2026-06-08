# ============================================================
#  RISE ETF 데이터 수집기 (RISE 홈페이지 기반)
# ============================================================

import re
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from config import RISE_BASE_URL, HEADERS, NAV_HISTORY_DAYS, DART_API_KEY, KRX_API_KEY
from krx_collector import KRXCollector, get_listing_date_from_krx, get_distribution_from_krx, get_distribution_from_naver

# DART 수집기 (분배금)
try:
    from dart_collector import DARTCollector as _DARTCollector
    _dart = _DARTCollector(DART_API_KEY)
    DART_OK = True
except Exception:
    DART_OK = False
    _dart = None


def _fetch_df(session, url):
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    try:
        tables = pd.read_html(BytesIO(resp.content), encoding="utf-8")
        return tables[0] if tables else None
    except Exception:
        return None


class RISECollector:
    def __init__(self, site_id):
        self.site_id = site_id
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.krx = KRXCollector(api_key=KRX_API_KEY)

    def get_nav_history(self, start_date=None):
        end = datetime.now().strftime("%Y-%m-%d")
        if start_date:
            sd = str(start_date).replace(".", "-").replace("/", "-")
            if len(sd) == 8 and "-" not in sd:
                sd = f"{sd[:4]}-{sd[4:6]}-{sd[6:]}"
            start = sd
        else:
            start = (datetime.now() - timedelta(days=NAV_HISTORY_DAYS)).strftime("%Y-%m-%d")

        url2 = (f"{RISE_BASE_URL}/prod/finder/productViewTabExcel2"
                f"?searchTargetId={self.site_id}"
                f"&searchStartDate={start}&searchEndDate={end}")
        url1 = f"{RISE_BASE_URL}/prod/finder/productViewTabExcel1?searchTargetId={self.site_id}"
        try:
            df2 = _fetch_df(self.session, url2)
            df1 = _fetch_df(self.session, url1)
            return self._merge_nav(df2, df1)
        except Exception as e:
            print(f"  [NAV 오류] {e}")
            return []

    def _merge_nav(self, df2, df1):
        def safe_float(v):
            try: return float(str(v).replace(",", ""))
            except: return None
        def safe_int(v):
            try: return int(float(str(v).replace(",", "")))
            except: return None

        def find_header_row(df):
            for i in range(min(10, len(df))):
                row = df.iloc[i].astype(str).tolist()
                if any("일자" in v for v in row):
                    return i
                if any(re.match(r'\d{4}\.\d{2}\.\d{2}', v) for v in row):
                    return max(0, i - 1)
            return 4

        def find_col(header_list, *keywords):
            for kw in keywords:
                for i, v in enumerate(header_list):
                    if kw in str(v):
                        return i
            return None

        records = {}

        if df2 is not None:
            hi2  = find_header_row(df2)
            h2   = df2.iloc[hi2].astype(str).tolist()
            c_date  = find_col(h2, "일자") or 1
            c_nav   = find_col(h2, "기준가격") or 2
            c_price = find_col(h2, "시장가격") or 4

            for _, row in df2.iloc[hi2 + 1:].iterrows():
                d = str(row.iloc[c_date]).strip()
                if not re.match(r'\d{4}\.\d{2}\.\d{2}', d):
                    continue
                nav_f = safe_float(row.iloc[c_nav])
                if nav_f is None or nav_f < 100:
                    continue
                records[d] = {
                    "date":   d,
                    "nav":    round(nav_f, 2),
                    "price":  safe_int(row.iloc[c_price]) if c_price < len(row) else None,
                    "volume": None,
                }

        if df1 is not None:
            hi1     = find_header_row(df1)
            h1      = df1.iloc[hi1].astype(str).tolist()
            c_date1 = find_col(h1, "일자") or 1
            c_vol   = find_col(h1, "거래량") or 5
            c_px1   = find_col(h1, "시장가격") or 4

            for _, row in df1.iloc[hi1 + 1:].iterrows():
                d = str(row.iloc[c_date1]).strip()
                if not re.match(r'\d{4}\.\d{2}\.\d{2}', d):
                    continue
                vol  = safe_int(row.iloc[c_vol])
                px1  = safe_int(row.iloc[c_px1])
                if d in records:
                    if vol:
                        records[d]["volume"] = vol
                    if records[d]["price"] is None and px1:
                        records[d]["price"] = px1

        return sorted(records.values(), key=lambda x: x["date"])

    def get_performance(self):
        url = f"{RISE_BASE_URL}/prod/finder/producProfitTabExcel2?searchTargetId={self.site_id}"
        perf = {k: None for k in ("1m","3m","6m","1y","3y","ytd","since_listing")}
        key_map = {"1개월":"1m","3개월":"3m","6개월":"6m","1년":"1y",
                   "3년":"3y","연초이후":"ytd","상장이후":"since_listing"}
        try:
            df = _fetch_df(self.session, url)
            if df is None: return perf

            header_idx = None
            for i in range(min(12, len(df))):
                row_str = df.iloc[i].astype(str).tolist()
                if any(k in row_str for k in key_map):
                    header_idx = i
                    break
            if header_idx is None:
                print("  [수익률 경고] 헤더 행 미발견")
                return perf

            header = df.iloc[header_idx].astype(str).tolist()

            nav_row = None
            for i in range(header_idx + 1, min(header_idx + 5, len(df))):
                row = df.iloc[i].tolist()
                row_str = [str(v) for v in row]
                num_count = sum(1 for v in row_str if re.match(r'^-?\d+\.?\d*$', v.strip()))
                if num_count >= 3:
                    nav_row = row
                    break

            if nav_row is None:
                print("  [수익률 경고] 데이터 행 미발견")
                return perf

            for i, col_name in enumerate(header):
                k = key_map.get(col_name.strip())
                if k and i < len(nav_row):
                    try:
                        val = float(str(nav_row[i]).replace(",", "").replace("%", ""))
                        perf[k] = round(val, 2)
                    except Exception:
                        pass
        except Exception as e:
            print(f"  [수익률 오류] {e}")
        return perf

    def get_daily_returns(self, rows=8):
        end   = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = (f"{RISE_BASE_URL}/prod/finder/productViewTabExcel2"
               f"?searchTargetId={self.site_id}"
               f"&searchStartDate={start}&searchEndDate={end}")
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
                records.append({"date": date_v, "nav": round(nav_f, 2),
                                 "return_pct": round(ret_f, 2)})

            records = sorted(records, key=lambda x: x["date"], reverse=True)
            if records:
                records = records[1:]
            return records[:rows]
        except Exception as e:
            print(f"  [일별수익률 오류] {e}")
            return []

    def get_holdings_and_meta(self):
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

    def _parse_page_meta(self, soup):
        meta = {}
        text = soup.get_text(" ")

        # 순자산 규모 (억원)
        aum_patterns = [
            r'순\s*자\s*산\s*규모[^0-9]{0,20}([0-9,]+)',
            r'순\s*자\s*산[^0-9]{0,10}([0-9,]+)\s*억',
            r'AUM[^0-9]{0,10}([0-9,]+)',
            r'총\s*자\s*산[^0-9]{0,20}([0-9,]+)',
        ]
        for pat in aum_patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(1).replace(",", "")
                try:
                    val = int(raw)
                    if val > 1_000_000_000:
                        meta["aum_display"] = f"{val // 100_000_000:,}"
                    elif val > 1_000_000:
                        meta["aum_display"] = f"{val // 10_000:,}"
                    elif val > 100:
                        meta["aum_display"] = f"{val:,}"
                    if "aum_display" in meta:
                        break
                except ValueError:
                    continue

        # 상장일 파싱 (label 바로 뒤 날짜 패턴)
        listing_patterns = [
            r'상장\s*일\s*자?\s*[:：]\s*(\d{4}[.\-]\d{2}[.\-]\d{2})',
            r'상장\s*일\s*자?\s+(\d{4}[.\-]\d{2}[.\-]\d{2})',
        ]
        for pat in listing_patterns:
            m = re.search(pat, text)
            if m:
                meta["listing_date"] = m.group(1).replace("-", ".")
                break

        return meta

    def get_distribution_history(self):
        """
        RISE 사이트 API에서 분배금 이력 자동 수집.
        성공: [{"date": "YYYY.MM.DD", "amount": float|None}, ...] (최신순)
        실패: [] → main.py에서 config fallback 처리
        """
        candidates = [
            f"{RISE_BASE_URL}/prod/finder/productDividendTabExcel?searchTargetId={self.site_id}",
            f"{RISE_BASE_URL}/prod/finder/productDividendTabExcel2?searchTargetId={self.site_id}",
        ]
        for url in candidates:
            try:
                df = _fetch_df(self.session, url)
                if df is None or len(df) < 2:
                    continue

                header_idx = None
                for i in range(min(10, len(df))):
                    row_str = df.iloc[i].astype(str).tolist()
                    joined = " ".join(row_str)
                    if any(k in joined for k in ("분배기준일", "기준일", "배당기준일", "지급일")):
                        header_idx = i
                        break
                if header_idx is None:
                    continue

                header = df.iloc[header_idx].astype(str).tolist()

                c_date = None
                for i, v in enumerate(header):
                    if any(k in v for k in ("분배기준일", "기준일", "배당기준일", "지급일", "일자")):
                        c_date = i; break
                if c_date is None:
                    c_date = 0

                c_amount = None
                for i, v in enumerate(header):
                    if any(k in v for k in ("분배금", "배당금", "1주당", "지급액", "금액")):
                        c_amount = i; break

                records = []
                for _, row in df.iloc[header_idx + 1:].iterrows():
                    d = str(row.iloc[c_date]).strip()
                    if not re.match(r'\d{4}[.\-]\d{2}[.\-]\d{2}', d):
                        continue
                    d = d.replace("-", ".")
                    amount = None
                    if c_amount is not None and c_amount < len(row):
                        try:
                            amount = float(str(row.iloc[c_amount]).replace(",", "").strip())
                        except (ValueError, TypeError):
                            pass
                    records.append({"date": d, "amount": amount})

                if records:
                    records = sorted(records, key=lambda x: x["date"], reverse=True)
                    print(f"  [분배금] {len(records)}건 자동 수집")
                    return records
            except Exception as e:
                print(f"  [분배금 오류] {e}")

        print(f"  [분배금] 자동 수집 실패 → config fallback 사용")
        return []

    def _parse_holdings(self, soup):
        holdings = []
        seen_names = set()

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue

            header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
            header_text  = " ".join(header_cells)
            if not any(kw in header_text for kw in ("종목명", "비중", "편입비", "구성종목")):
                continue

            w_col = None
            for i, h in enumerate(header_cells):
                if any(kw in h for kw in ("비중", "편입비", "비율")):
                    w_col = i; break

            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) < 2:
                    continue

                weight_val = None
                candidates_cells = [cells[w_col]] if w_col and w_col < len(cells) else []
                candidates_cells += [c for c in reversed(cells) if c not in candidates_cells]
                for cell in candidates_cells:
                    clean = cell.replace("%", "").replace(",", "").strip()
                    if re.match(r'^\d{1,3}\.\d{1,2}$', clean):
                        try:
                            w = float(clean)
                            if 0 < w < 100:
                                weight_val = w; break
                        except ValueError:
                            pass
                if weight_val is None:
                    continue

                name = ""
                for cell in cells:
                    if (len(cell) > len(name)
                            and not re.match(r'^[\d,%.]+$', cell)
                            and not re.match(r'^KR', cell)):
                        name = cell
                if not name or "현금" in name or "합계" in name:
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)

                ticker = ""
                for cell in cells:
                    m = re.match(r'KR7(\d{6})', cell)
                    if m:
                        ticker = m.group(1); break

                rank = len(holdings) + 1
                if cells and re.match(r'^\d+$', cells[0]):
                    try: rank = int(cells[0])
                    except: pass

                holdings.append({"rank": rank, "name": name, "ticker": ticker, "weight": weight_val})

            if holdings:
                break

        holdings = sorted(holdings, key=lambda x: x["weight"], reverse=True)[:10]
        for i, h in enumerate(holdings):
            h["rank"] = i + 1
        return holdings

    @staticmethod
    def calc_avg_volume(nav_history, days=20):
        vols = [r["volume"] for r in nav_history if r.get("volume")]
        recent = vols[-days:]
        if not recent:
            return None
        return int(sum(recent) / len(recent))

    def collect_all(self, etf_config=None):
        print(f"  [수집 시작] site_id={self.site_id}")
        etf_config = etf_config or {}
        cfg_listing = etf_config.get("listing_date", "")

        # 1. holdings + page_meta 먼저 수집 (상장일 스크래핑 포함)
        holdings, page_meta = self.get_holdings_and_meta()
        holdings = self.krx.enrich_holdings(holdings)

        # 2. 상장일: KRX API → RISE 페이지 스크래핑 → config fallback
        ticker_6 = etf_config.get("ticker", "")
        scraped_listing = page_meta.get("listing_date")   # "YYYY.MM.DD"

        krx_listing = ""
        if ticker_6:
            try:
                krx_listing = get_listing_date_from_krx(ticker_6, KRX_API_KEY)
                if krx_listing:
                    print(f"  [상장일 KRX] {krx_listing}")
            except Exception as e:
                print(f"  [상장일 KRX 오류] {e}")

        # 상장일 우선순위: KRX API > config(사람이 검증) > 스크래핑
        if krx_listing:
            effective_listing = krx_listing.replace(".", "-")
            page_meta["listing_date"] = krx_listing
            if cfg_listing and effective_listing != cfg_listing:
                print(f"  [상장일 불일치] KRX={krx_listing} | config={cfg_listing}")
        elif cfg_listing:
            # config가 있으면 스크래핑보다 우선 (검증된 값)
            effective_listing = cfg_listing
            page_meta["listing_date"] = cfg_listing.replace("-", ".")
            if scraped_listing and scraped_listing.replace(".", "-") != cfg_listing:
                print(f"  [상장일] 스크래핑({scraped_listing}) ≠ config({cfg_listing}) → config 사용")
        elif scraped_listing:
            effective_listing = scraped_listing.replace(".", "-")
            page_meta["listing_date"] = scraped_listing
            print(f"  [상장일] config 없음 → 스크래핑 사용: {scraped_listing}")
        else:
            effective_listing = ""
            print(f"  [상장일] 모든 소스 실패")

        # 3. NAV / 수익률 / 일별 수익률
        nav   = self.get_nav_history(start_date=effective_listing or None)
        perf  = self.get_performance()
        daily = self.get_daily_returns()

        # 4. 분배금 수집 — 템플릿에서 제거됨, 수집 생략
        distribution_history = []

        # 5. BM 지수 데이터
        bm_name = self.krx.determine_bm(holdings)
        if effective_listing:
            listing_date_ymd = effective_listing.replace(".", "").replace("-", "")
        elif nav:
            listing_date_ymd = nav[0]["date"].replace(".", "")
        else:
            listing_date_ymd = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        today   = datetime.now().strftime("%Y%m%d")
        bm_data = self.krx.get_index_data(listing_date_ymd, today, bm_name)

        sector_data = KRXCollector.aggregate_sectors(holdings)
        avg_vol_20  = self.calc_avg_volume(nav, days=20)

        tradeable = [r for r in nav if r.get("price")]
        latest    = tradeable[-1] if tradeable else {}

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
            "page_meta":            page_meta,
            "aum_raw":              page_meta.get("aum_display"),
            "distribution_history": distribution_history or None,
            "sector_data":          sector_data,
            "avg_volume_20d":       avg_vol_20,
            "latest":               latest,
        }
