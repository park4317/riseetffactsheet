# ============================================================
#  RISE ETF 팩트시트 자동화 — 실행 진입점
#
#  사용법:
#    python main.py                          # 전체 국내주식형 생성
#    python main.py "RISE 현대차고정피지컬AI"  # 특정 ETF만 생성
#    python main.py --test                   # 수집만 (HTML 미생성)
# ============================================================

import sys
import os
from datetime import datetime

from config    import ETF_LIST, OUTPUT_DIR
from collector import RISECollector
from news      import NaverNewsCollector
from renderer  import FactsheetRenderer


def generate_factsheet(etf_name: str, test_mode: bool = False) -> dict | None:
    if etf_name not in ETF_LIST:
        print(f"[오류] '{etf_name}'이 config.py에 없습니다.")
        print(f"  등록된 ETF: {list(ETF_LIST.keys())}")
        return None

    cfg = ETF_LIST[etf_name]
    print(f"\n{'='*60}")
    print(f"  {etf_name}  ({cfg['ticker']})")
    print(f"{'='*60}")

    # ── 1. RISE 사이트 데이터 수집
    collector = RISECollector(cfg["site_id"])
    data = collector.collect_all(etf_config={**cfg, "name": etf_name})

    # ── 2. 뉴스 수집 (ETF + 구성종목 + 매크로)
    from news import NewsCollector
    nc = NewsCollector()
    news_bundle = nc.collect_for_etf({**cfg, "name": etf_name}, holdings=data.get("holdings", []))
    data["news_bundle"] = news_bundle
    total_news = sum(len(v) for v in news_bundle.values())
    print(f"  뉴스: ETF {len(news_bundle['etf'])}건 / 종목 {len(news_bundle['stocks'])}건 / 매크로 {len(news_bundle['macro'])}건")

    # ── 3. config에서 정적 정보 보완
    data.setdefault("aum_raw", cfg.get("aum_display"))

    if test_mode:
        import json
        print("\n[TEST] 수집 완료 — HTML 미생성")
        print(f"  NAV {len(data['nav_history'])}일 | 구성종목 {len(data['holdings'])}개 | "
              f"수익률({data['display_return_label']}) {data['display_return']}%")
        return data

    # ── 4. HTML 렌더링
    renderer = FactsheetRenderer()
    out_path  = renderer.render(etf_name, cfg, data)
    print(f"  → {out_path}")
    return {"etf": etf_name, "output": out_path, "data": data}


def main():
    args      = sys.argv[1:]
    test_mode = "--test" in args
    args      = [a for a in args if a != "--test"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start = datetime.now()

    if args:
        etf_name = " ".join(args)
        generate_factsheet(etf_name, test_mode=test_mode)
    else:
        targets = [n for n, c in ETF_LIST.items() if c["category"] == "국내주식"]
        print(f"[실행] 국내주식형 ETF {len(targets)}개 팩트시트 생성")
        for name in targets:
            generate_factsheet(name, test_mode=test_mode)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"[완료] {elapsed:.1f}초")


if __name__ == "__main__":
    main()
