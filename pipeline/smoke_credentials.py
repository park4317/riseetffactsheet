# -*- coding: utf-8 -*-
"""OpenDART / KRX 자격증명 read-only 스모크 테스트.

  python pipeline/smoke_credentials.py

**HTTP 200 을 성공으로 치지 않는다.**

2026-09-06 종목→ETF 매핑 사고가 그 차이에서 났다. 티커 목록은 200 으로 내려왔고
파싱도 됐지만 비중과 시가총액이 전부 0이었다. 그래도 실행은 성공으로 기록됐다.
DART 는 한술 더 떠서 **키가 틀려도 HTTP 200 을 주고** 본문 status 로만 알려준다.

그래서 여기서는 세 겹으로 본다.
  1. 응답이 왔는가
  2. 응답 본문이 성공을 말하는가 (DART status, KRX OutBlock 존재)
  3. **내용이 실제 값인가** — 행이 있고, 그 안의 숫자가 0이 아닌가

키 값은 읽어서 헤더에만 넣는다. 출력하지 않는다. 길이도 찍지 않는다.
조회만 하고 아무것도 쓰지 않는다.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (DART_API_KEY_ENV, KRX_API_KEY_ENV,  # noqa: E402
                    MissingCredential, require_api_key)

KST = datetime.timezone(datetime.timedelta(hours=9))
TIMEOUT = 30

# DART 응답 status 코드. 000 만 성공이고 나머지는 전부 실패다.
_DART_STATUS = {
    "000": "정상",
    "010": "등록되지 않은 키",
    "011": "사용할 수 없는 키",
    "012": "접근할 수 없는 IP",
    "013": "조회된 데이터 없음",
    "020": "요청 제한 초과",
    "100": "필드 부적절",
    "800": "시스템 점검 중",
    "900": "정의되지 않은 오류",
    "901": "사용자 계정의 개인정보보유기간 만료",
}


def _get_json(url: str, headers: dict | None = None) -> tuple:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"_body": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:                                     # noqa: BLE001
        return 0, {"_error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────── OpenDART ───────────────────────────────

def check_dart() -> tuple:
    """(ok, 한 줄 요약). 키 값은 어디에도 남기지 않는다."""
    try:
        key = require_api_key(DART_API_KEY_ENV, service="OpenDART")
    except MissingCredential as e:
        return False, str(e)

    end = datetime.datetime.now(KST).date()
    bgn = end - datetime.timedelta(days=14)
    url = "https://opendart.fss.or.kr/api/list.json?" + urllib.parse.urlencode({
        "crtfc_key": key,
        "bgn_de": bgn.strftime("%Y%m%d"),
        "end_de": end.strftime("%Y%m%d"),
        "corp_cls": "Y",          # 유가증권
        "page_count": "10",
    })
    status, body = _get_json(url)

    # ① 응답
    if status != 200:
        return False, f"HTTP {status} — {str(body)[:120]}"

    # ② 본문이 성공을 말하는가. **DART 는 키가 틀려도 200 을 준다.**
    code = str(body.get("status", ""))
    if code != "000":
        return False, (f"HTTP 200 이지만 본문 status={code} "
                       f"({_DART_STATUS.get(code, '알 수 없는 코드')})")

    # ③ 내용이 실제 값인가
    items = body.get("list") or []
    if not items:
        return False, "status=000 이지만 공시 목록이 비어 있음"
    sample = items[0]
    for field in ("rcept_no", "corp_name", "rcept_dt"):
        if not sample.get(field):
            return False, f"공시 항목에 {field} 가 없음 — 응답 구조가 바뀌었을 수 있음"

    return True, (f"공시 {len(items)}건 조회 (최근 {sample['rcept_dt']}, "
                  f"예: {sample['corp_name']})")


# ───────────────────────────────── KRX ─────────────────────────────────

def check_krx() -> tuple:
    try:
        key = require_api_key(KRX_API_KEY_ENV, service="KRX Open API")
    except MissingCredential as e:
        return False, str(e)

    base = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
    headers = {"AUTH_KEY": key, "User-Agent": "jkos-smoke/0.1"}

    day = datetime.datetime.now(KST).date()
    tried = []
    for _ in range(10):                    # 주말·휴장일을 건너뛰며 뒤로 물러난다
        if day.weekday() >= 5:
            day -= datetime.timedelta(days=1)
            continue
        bas = day.strftime("%Y%m%d")
        tried.append(bas)
        status, body = _get_json(f"{base}?basDd={bas}", headers)

        # ① 응답
        if status in (401, 403):
            return False, f"HTTP {status} — 인증 실패 (키가 아직 활성화되지 않았을 수 있음)"
        if status != 200:
            return False, f"HTTP {status} — {str(body)[:120]}"

        # ② 본문 구조
        rows = body.get("OutBlock_1")
        if rows is None:
            return False, f"HTTP 200 이지만 OutBlock_1 이 없음 — {str(body)[:120]}"
        if not rows:
            day -= datetime.timedelta(days=1)
            continue                        # 그날 발행이 없다. 다음 날짜로.

        # ③ 내용이 실제 값인가 — **행이 있다는 것과 값이 있다는 것은 다르다**
        if len(rows) < 100:
            return False, f"{bas}: 행이 {len(rows)}개뿐 — 전종목 시세로 보기에 너무 적음"
        priced = 0
        for r in rows[:200]:
            try:
                if float(str(r.get("TDD_CLSPRC", "0")).replace(",", "")) > 0:
                    priced += 1
            except ValueError:
                pass
        if priced == 0:
            return False, (f"{bas}: {len(rows)}행을 받았지만 종가가 전부 0 — "
                           f"09-06 사고와 같은 형태다. 발행 전 데이터일 수 있음")
        return True, (f"{bas} 전종목 {len(rows)}행, 표본 200건 중 "
                      f"종가>0 이 {priced}건")

    return False, f"최근 영업일에서 발행된 데이터를 찾지 못함 (조회 시도: {tried})"


def main() -> int:
    print("OpenDART / KRX 자격증명 스모크 테스트 (read-only)")
    print("키 값은 출력하지 않습니다.\n")
    results = []
    for label, fn in (("OpenDART", check_dart), ("KRX Open API", check_krx)):
        ok, detail = fn()
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:14} {detail}")
    print()
    if all(results):
        print("두 키 모두 정상 — 응답·본문상태·데이터내용 세 겹 확인")
        return 0
    print("실패한 항목이 있습니다. 위 사유를 확인하세요.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
