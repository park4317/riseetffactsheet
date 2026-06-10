# ============================================================
#  HTML 렌더러 — 수집 데이터 → Jinja2 팩트시트 HTML
# ============================================================

import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from config import OUTPUT_DIR

SECTOR_COLORS = [
    "#0047B3","#F5A800","#4A9CF0","#28A745",
    "#E03232","#6C757D","#17A2B8","#FD7E14",
    "#6F42C1","#20C997","#343A40","#FF6B9D",
]


def _fmt_pct(v):
    if v is None: return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"

def _fmt_number(v):
    if v is None: return "—"
    return f"{v:,.0f}"

def _sector_color(i):
    return SECTOR_COLORS[int(i) % len(SECTOR_COLORS)]


class FactsheetRenderer:
    def __init__(self, template_dir: str = None):
        base    = os.path.dirname(__file__)
        tpl_dir = template_dir or os.path.join(base, "..", "templates")
        self.env = Environment(
            loader=FileSystemLoader(tpl_dir),
            autoescape=False,   # JS/JSON 주입이 많아 False 사용
        )
        self.env.filters["fmt_pct"]      = _fmt_pct
        self.env.filters["fmt_number"]   = _fmt_number
        self.env.filters["sector_color"] = _sector_color

    def render(self, etf_name: str, etf_config: dict, data: dict) -> str:
        template = self.env.get_template("factsheet.html")

        nav     = data.get("nav_history", [])
        bm      = data.get("bm_history", [])
        perf    = data.get("performance", {})
        hold    = data.get("holdings", [])
        sectors = data.get("sector_data", [])
        latest  = data.get("latest", {})
        avg_vol = data.get("avg_volume_20d")

        # 상장일: page_meta > config > nav 첫 날짜
        page_meta     = data.get("page_meta", {})
        _cfg_listing  = (etf_config.get("listing_date", "") or "").replace("-", ".")
        listing_str   = (page_meta.get("listing_date") or _cfg_listing
                         or (nav[0]["date"] if nav else "—"))

        # 평균 거래량 → 만주 단위
        avg_vol_fmt   = f"{avg_vol // 10000:,.0f}" if avg_vol else "—"

        # 순자산: 스크래핑 우선 → config → —
        aum_display   = data.get("aum_raw") or etf_config.get("aum_display") or "—"

        # 총보수: config 우선
        expense_ratio = etf_config.get("expense_ratio", "—")
        if isinstance(expense_ratio, float):
            expense_ratio = f"{expense_ratio:.2f}"

        # 구성종목수: config 우선 (실제 전체), 없으면 수집 TOP10
        holding_count = etf_config.get("holding_count") or len(hold)

        # 업종 차트용 JSON
        s_labels  = json.dumps([s["sector"] for s in sectors], ensure_ascii=False)
        s_weights = json.dumps([s["weight"] for s in sectors])
        s_colors  = json.dumps([SECTOR_COLORS[i % len(SECTOR_COLORS)] for i in range(len(sectors))])

        # ── 추가 성과 통계 (거래일 기준, Excel2 정확 데이터) ──
        trade_nav = [(r["nav"], r["date"], r.get("price"))
                     for r in nav if r.get("price") and r.get("nav")]
        if trade_nav:
            nav_hi  = max(trade_nav, key=lambda x: x[0])
            nav_lo  = min(trade_nav, key=lambda x: x[0])
            # 괴리율: |(price - nav)| / nav * 100 (Excel2로 정확히 계산)
            spreads = [abs(p - n) / n * 100 for n, _, p in trade_nav if p]
            avg_spread = round(sum(spreads) / len(spreads), 2) if spreads else None
        else:
            nav_hi = nav_lo = None
            avg_spread = None

        # 상장 경과일
        try:
            from datetime import date as _date
            lst = _date.fromisoformat(listing_str.replace(".", "-"))
            nav_period_days = (_date.today() - lst).days
        except Exception:
            nav_period_days = 0

        # ── BM 기간별 수익률 (수익률 표 KOSPI 행용) ──
        bm_perf = self._calc_bm_returns(bm)

        # ── 뉴스 번들 분리 ──
        news_bundle = data.get("news_bundle", {})
        news_etf    = news_bundle.get("etf", data.get("news", []))
        news_stocks = news_bundle.get("stocks", [])
        news_macro  = news_bundle.get("macro", [])

        # ── 일별 거래 테이블 (거래일만, 전일까지 8개) ──
        daily_table = [
            r for r in reversed(nav) if r.get("price")
        ][1:9]

        ctx = {
            "etf_name":    etf_name,
            "etf_config":  etf_config,
            "base_date":   datetime.now().strftime("%Y. %m. %d"),

            # 기본 정보
            "listing_date":    listing_str,
            "expense_ratio":   expense_ratio,
            "holding_count":   holding_count,
            "aum_display":     aum_display,
            "avg_vol_fmt":     avg_vol_fmt,

            # 수익률
            "performance":             perf,
            "display_return":          data.get("display_return"),
            "display_return_label":    data.get("display_return_label", "상장이후"),

            # 차트 데이터 (JSON)
            "nav_all_json": json.dumps(nav, ensure_ascii=False),
            "bm_all_json":  json.dumps(bm,  ensure_ascii=False),
            "bm_name":      data.get("bm_name", "KOSPI"),

            # 구성종목
            "holdings":    hold,

            # 업종
            "sector_data":         sectors,
            "sector_labels_json":  s_labels,
            "sector_weights_json": s_weights,
            "sector_colors_json":  s_colors,

            # 추가 성과 지표
            "nav_high":        {"nav": nav_hi[0], "date": nav_hi[1]} if nav_hi else None,
            "nav_low":         {"nav": nav_lo[0], "date": nav_lo[1]} if nav_lo else None,
            "avg_spread":      avg_spread,
            "nav_period_days": nav_period_days,

            # BM 기간별 수익률 (KOSPI 행)
            "bm_performance": bm_perf,

            # 뉴스 (분리)
            "news_etf":    news_etf,
            "news_stocks": news_stocks,
            "news_macro":  news_macro,

            # 일별 NAV 테이블
            "daily_returns": daily_table,
        }

        html = template.render(**ctx)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        safe  = etf_name.replace(" ", "_").replace("/", "-")
        dstr  = datetime.now().strftime("%Y%m%d")
        fname = f"factsheet_{safe}_{dstr}.html"
        path  = os.path.join(OUTPUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [저장] {path}")
        return path

    @staticmethod
    def _calc_bm_returns(bm_data: list[dict]) -> dict:
        """BM(KOSPI/KOSDAQ) 이력에서 기간별 수익률 계산"""
        perf = {k: None for k in ("1m","3m","6m","1y","3y","ytd","since_listing")}
        if not bm_data:
            return perf
        bm_map = {r["date"]: r["close"] for r in bm_data}
        sorted_dates = sorted(bm_map.keys())
        if len(sorted_dates) < 2:
            return perf
        latest_val = bm_map[sorted_dates[-1]]
        first_val  = bm_map[sorted_dates[0]]
        # 상장이후
        if first_val:
            perf["since_listing"] = round((latest_val / first_val - 1) * 100, 2)
        # 기간별 (거래일 근사)
        for key, days in {"1m": 22, "3m": 66, "6m": 132, "1y": 252}.items():
            if len(sorted_dates) > days:
                base = bm_map[sorted_dates[-days - 1]]
                perf[key] = round((latest_val / base - 1) * 100, 2)
        return perf
