# ============================================================
#  뉴스 수집기
#  Primary: Google News RSS (안정적, API키 불필요)
#  Fallback: 네이버 뉴스 검색
# ============================================================

import re
import time
import xml.etree.ElementTree as ET
import urllib.parse
import requests
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from config import HEADERS, NEWS_COUNT

# 매크로 뉴스 기본 키워드 (국내주식형 공통)
MACRO_KEYWORDS = [
    "코스피 시황",
    "미 연준 금리",
    "원달러 환율",
]


class NewsCollector:
    """
    Google News RSS 기반 뉴스 수집기
    ETF 뉴스 + 구성종목 뉴스 + 매크로 뉴스 통합 제공
    """

    GOOGLE_RSS = "https://news.google.com/rss/search"
    NAVER_SEARCH = "https://search.naver.com/search.naver"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            **HEADERS,
            "Accept": "application/rss+xml,text/html,*/*",
        })

    # ── Google News RSS (primary) ─────────────────────────
    def search_rss(self, keyword: str, count: int = 5) -> list[dict]:
        """Google News RSS로 최신 뉴스 검색"""
        params = {
            "q":    keyword,
            "hl":   "ko",
            "gl":   "KR",
            "ceid": "KR:ko",
        }
        try:
            resp = self.session.get(self.GOOGLE_RSS, params=params, timeout=10)
            resp.raise_for_status()
            return self._parse_rss(resp.content, count)
        except Exception as e:
            print(f"  [Google RSS 실패] '{keyword}': {e}")
            return self._search_naver(keyword, count)   # 폴백

    def _is_recent(self, date_str: str, days: int = 7) -> bool:
        """날짜가 최근 N일 이내인지 확인"""
        if not date_str:
            return True
        try:
            pub = datetime.strptime(date_str, "%Y.%m.%d")
            return (datetime.now() - pub).days <= days
        except Exception:
            return True

    def _parse_rss(self, content: bytes, count: int) -> list[dict]:
        """RSS XML 파싱"""
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        ns = {"media": "http://search.yahoo.com/mrss/"}
        channel = root.find("channel")
        if channel is None:
            return []

        articles = []
        for item in channel.findall("item")[:count]:
            title = item.findtext("title", "").strip()
            # Google RSS 제목은 "뉴스제목 - 언론사" 형태
            if " - " in title:
                headline, press = title.rsplit(" - ", 1)
            else:
                headline, press = title, ""

            link = item.findtext("link", "").strip()
            pub  = item.findtext("pubDate", "")
            date = ""
            if pub:
                try:
                    date = parsedate_to_datetime(pub).strftime("%Y.%m.%d")
                except Exception:
                    date = pub[:10]

            # source 태그에 언론사 있으면 우선 사용
            src = item.find("source")
            if src is not None and src.text:
                press = src.text.strip()

            if headline:
                articles.append({
                    "title": headline,
                    "url":   link,
                    "press": press,
                    "date":  date,
                    "stock": "",
                })
        return articles

    # ── Naver 검색 (fallback) ─────────────────────────────
    def _search_naver(self, keyword: str, count: int) -> list[dict]:
        params = {"where": "news", "query": keyword, "sort": "1"}
        try:
            resp = self.session.get(self.NAVER_SEARCH, params=params, timeout=10)
            soup = BeautifulSoup(resp.text, "lxml")
            articles = []

            for item in soup.select("ul.list_news li.bx")[:count]:
                a = (item.select_one("a.news_tit") or
                     item.select_one("a.api_txt_lines"))
                if not a:
                    continue
                title = a.get_text(strip=True)
                url   = a.get("href", "")
                press_el = item.select_one("a.info.press")
                press = press_el.get_text(strip=True) if press_el else ""
                date  = ""
                for sel in ["span.info", "span.date"]:
                    d = item.select_one(sel)
                    if d:
                        m = re.search(r'\d{4}\.\d{2}\.\d{2}|\d+[시간분일]+ 전',
                                      d.get_text())
                        if m:
                            date = m.group(); break
                if title:
                    articles.append({"title": title, "url": url,
                                     "press": press, "date": date, "stock": ""})
            return articles
        except Exception:
            return []

    # ── 통합 수집 ─────────────────────────────────────────
    def collect_for_etf(self, etf_config: dict,
                        holdings: list[dict] | None = None,
                        include_macro: bool = True) -> dict:
        """
        ETF 뉴스 + 구성종목 뉴스 + 매크로 뉴스 수집
        반환: {
          "etf":     [ETF 자체 뉴스],
          "stocks":  [구성종목 관련 뉴스],
          "macro":   [매크로/시장 뉴스],
        }
        """
        seen = set()

        def dedup(articles, stock=""):
            out = []
            for a in articles:
                key = a["title"][:30]
                if key not in seen:
                    seen.add(key)
                    a["stock"] = stock
                    out.append(a)
            return out

        # ① ETF 자체 뉴스 (2개)
        kw0 = etf_config.get("news_keywords", [""])[0]
        etf_news = dedup(self.search_rss(kw0, count=3))[:2]

        # ② 추가 ETF 키워드 (1개씩)
        for kw in etf_config.get("news_keywords", [])[1:]:
            if len(etf_news) >= 3:
                break
            etf_news += dedup(self.search_rss(kw, count=2))[:1]
            time.sleep(0.3)

        # ③ 구성종목 뉴스 (상위 3종목, 각 1개)
        stock_news = []
        if holdings:
            for h in [h for h in holdings[:5] if "현금" not in h.get("name","")][:3]:
                name = h.get("name", "")
                arts = self.search_rss(f"{name} 주가", count=3)
                stock_news += dedup(arts, stock=name)[:1]
                time.sleep(0.3)

        # ④ 매크로 뉴스 (최근 7일 이내만, 2개)
        macro_news = []
        if include_macro:
            macro_kws = etf_config.get("macro_keywords", MACRO_KEYWORDS)
            for kw in macro_kws[:2]:
                arts = self.search_rss(kw, count=5)
                recent = [a for a in arts if self._is_recent(a.get("date",""), days=7)]
                macro_news += dedup(recent)[:1]
                time.sleep(0.3)

        return {
            "etf":    etf_news[:3],
            "stocks": stock_news[:3],
            "macro":  macro_news[:2],
        }


# 하위 호환 alias
NaverNewsCollector = NewsCollector
