# ============================================================
#  RISE ETF 팩트시트 자동화 — ETF 설정
#  새 ETF 추가: ETF_LIST에 항목 추가 후 app.py 재시작
# ============================================================

ETF_LIST = {

    # ══════════════════════════════════════════════════
    #  국내주식 — 대표지수
    # ══════════════════════════════════════════════════
    "RISE 200": {
        "site_id": "4435", "ticker": "102110", "category": "국내주식",
        "keywords": ["코스피200", "대표지수", "국내대형주"],
        "description": "코스피200 지수를 추종하는 국내 대표 대형주 ETF",
        "index_name": "코스피200 지수",
        "news_keywords": ["코스피200 ETF", "코스피 시황"],
    },
    "RISE 200TR": {
        "site_id": "44A5", "ticker": "361580", "category": "국내주식",
        "keywords": ["코스피200", "토탈리턴", "배당재투자"],
        "description": "코스피200 토탈리턴 지수 추종 — 배당 자동 재투자 구조",
        "index_name": "코스피200 TR 지수",
        "news_keywords": ["RISE 200TR ETF", "코스피200 배당재투자"],
    },
    "RISE 코스피": {
        "site_id": "4489", "ticker": "228790", "category": "국내주식",
        "keywords": ["코스피", "전체시장", "국내주식"],
        "description": "코스피 전체 시장을 추종하는 국내 주식 ETF",
        "index_name": "코스피 지수",
        "news_keywords": ["코스피 시황", "국내 증시"],
    },
    "RISE KRX300": {
        "site_id": "4481", "ticker": "244620", "category": "국내주식",
        "keywords": ["KRX300", "코스피", "코스닥", "대중형주"],
        "description": "코스피·코스닥 대표 300종목에 투자하는 국내 통합지수 ETF",
        "index_name": "KRX300 지수",
        "news_keywords": ["KRX300 ETF", "코스피 코스닥 시황"],
    },
    "RISE 코스닥150": {
        "site_id": "4459", "ticker": "232080", "category": "국내주식",
        "keywords": ["코스닥150", "코스닥", "중소형성장주"],
        "description": "코스닥150 지수를 추종하는 코스닥 대표 ETF",
        "index_name": "코스닥150 지수",
        "news_keywords": ["코스닥150 ETF", "코스닥 시황"],
    },

    # ══════════════════════════════════════════════════
    #  국내주식 — 테마
    # ══════════════════════════════════════════════════
    "RISE 현대차고정피지컬AI": {
        "site_id": "44K4", "ticker": "0190C0", "category": "국내주식",
        "keywords": ["피지컬AI", "현대차그룹", "로보틱스", "자율주행", "공장자동화"],
        "description": (
            "피지컬AI 생태계의 핵심, 현대차에 25% 고정 편입 - "
            "자율주행·로보틱스·공장자동화를 선도하는 국내 기업에 집중 투자"
        ),
        "index_name": "KEDI 현대차고정피지컬AI 지수",
        "methodology": [
            "현대차 <b>25% 고정</b> 편입 - 피지컬AI 생태계 핵심 기업으로 고정 비중 투자",
            "<b>LLM 기반 유사도 스코어링</b> - 공시보고서에 LLM 적용, 피지컬AI 키워드 유사도로 종목 선정",
            "<b>시총 가중 + 개별 종목 15% 상한</b>",
            "<b>총 15종목</b> 구성 (6개월 주기 리밸런싱)",
        ],
        "distribution": "1·4·7·10월<br>마지막 영업일",
        "outlook_pos": [
            "현대차그룹, 보스턴다이내믹스 중심 글로벌 로보틱스 생태계 구축 가속",
            "외국인 자금 피지컬AI 섹터 집중 유입",
            "두산로보틱스 북미 수주 급증",
            "레인보우로보틱스 삼성전자 전략 투자 후 기술력 강화",
        ],
        "outlook_neg": [
            "현대차그룹 계열 합산 51%+ 그룹 집중 리스크",
            "신규 상장(26.05.12) ETF로 트랙레코드 미형성",
            "로보틱스 테마 변동성 - 단기 +-15% 발생 가능",
            "LLM 기반 지수 편입으로 리밸런싱 시 종목 변경 가능성",
        ],
        "expense_ratio": 0.40, "holding_count": 15,
        "rebalancing_period": "6개월 (연 2회)",
        "distribution_history": [],
        "news_keywords": ["RISE 현대차고정피지컬AI", "현대차 피지컬AI 로봇", "두산로보틱스 레인보우로보틱스"],
    },
    "RISE 네트워크인프라": {
        "site_id": "44A7", "ticker": "367760", "category": "국내주식",
        "keywords": ["AI 인프라", "5G", "반도체 부품", "광통신", "AI 서버"],
        "description": (
            "5G·AI 시대 연결 인프라의 핵심 - 삼성전기·SK하이닉스·LG이노텍 등 "
            "AI 서버 핵심 부품 및 네트워크 밸류체인 기업에 집중 투자"
        ),
        "index_name": "FnGuide 네트워크인프라 지수",
        "methodology": [
            "<b>텍스트 마이닝 기반 종목 선별</b> - 5G·AI 관련성 높은 종목 추출",
            "<b>유동성·사이즈 필터</b> - 60일 평균거래대금 2억원 이상, 시총 500억원 이상",
            "<b>유동시총 가중 + 종목별 20% 상한</b>",
            "<b>통신사업자(KT·SKT) 제외</b>",
        ],
        "distribution": "1·4·7·10월<br>마지막 영업일",
        "outlook_pos": [
            "빅테크 CapEx 사이클 지속 - AI 서버 증설 수요로 MLCC·HBM 동반 수혜",
            "삼성전기, AI서버용 MLCC 수요 폭증",
            "SK하이닉스 HBM3E/HBM4 본격 양산",
            "이수페타시스·대한광통신, 광통신 인프라 투자 확대 수혜",
        ],
        "outlook_neg": [
            "상위 3개 종목(삼성전기+SK하이닉스+삼성전자) 합산 73.3%",
            "실질 포트폴리오는 AI 반도체 부품 중심으로 전환",
            "단기 변동성 - 1개월 내 +-15~30% 등락",
            "반도체 다운사이클 시 동반 조정 가능",
        ],
        "expense_ratio": 0.45, "holding_count": 23,
        "rebalancing_period": "반기 (연 2회)",
        "distribution_history": ["2026.04.30", "2025.04.30"],
        "news_keywords": ["RISE 네트워크인프라 ETF", "삼성전기 AI서버 MLCC", "SK하이닉스 HBM 수요"],
        "macro_keywords": ["빅테크 CapEx AI 서버", "삼성전자 반도체 수출"],
    },
    "RISE AI전력인프라": {
        "site_id": "44J3", "ticker": "0094L0", "category": "국내주식",
        "keywords": ["AI", "전력", "인프라", "데이터센터", "변압기"],
        "description": "AI 데이터센터 확산에 따른 전력 인프라 수요 수혜 기업 투자",
        "index_name": "iSelect AI전력인프라 지수",
        "news_keywords": ["AI 전력인프라 ETF", "데이터센터 전력 수혜", "변압기 수요"],
    },
    "RISE AI반도체TOP10": {
        "site_id": "44J0", "ticker": "", "category": "국내주식",
        "keywords": ["AI반도체", "HBM", "반도체", "TOP10"],
        "description": "국내 AI 반도체 대표 기업 상위 10종목에 집중 투자",
        "index_name": "AI반도체TOP10 지수",
        "news_keywords": ["RISE AI반도체TOP10", "국내 AI 반도체 주식"],
    },
    "RISE 비메모리반도체액티브": {
        "site_id": "44B9", "ticker": "388420", "category": "국내주식",
        "keywords": ["비메모리", "시스템반도체", "파운드리", "팹리스"],
        "description": "시스템반도체·파운드리·팹리스 등 비메모리 반도체 밸류체인 투자",
        "index_name": "액티브 운용 (비메모리반도체)",
        "news_keywords": ["RISE 비메모리반도체 ETF", "시스템반도체 수주", "파운드리"],
    },
    "RISE AI&로봇": {
        "site_id": "44F5", "ticker": "", "category": "국내주식",
        "keywords": ["AI", "로봇", "자동화", "인공지능"],
        "description": "국내 AI·로봇 테마 대표 기업에 투자하는 ETF",
        "index_name": "KRX AI&로봇 지수",
        "news_keywords": ["RISE AI로봇 ETF", "국내 AI 로봇 주식"],
    },
    "RISE AI플랫폼": {
        "site_id": "44C9", "ticker": "", "category": "국내주식",
        "keywords": ["AI플랫폼", "플랫폼", "인터넷", "빅테크"],
        "description": "국내 플랫폼 비즈니스 경쟁우위 핵심기업에 투자하는 ETF",
        "index_name": "AI플랫폼 지수",
        "news_keywords": ["RISE AI플랫폼 ETF", "국내 플랫폼 주식"],
    },
    "RISE 삼성전자단일종목레버리지": {
        "site_id": "44K5", "ticker": "", "category": "국내주식",
        "keywords": ["삼성전자", "레버리지", "단일종목"],
        "description": "삼성전자 일간 수익률의 2배 수익을 추구하는 레버리지 ETF",
        "index_name": "삼성전자 레버리지 지수",
        "news_keywords": ["삼성전자 주가", "반도체 업황"],
    },
    "RISE SK하이닉스단일종목레버리지": {
        "site_id": "44K6", "ticker": "", "category": "국내주식",
        "keywords": ["SK하이닉스", "레버리지", "HBM", "단일종목"],
        "description": "SK하이닉스 일간 수익률의 2배 수익을 추구하는 레버리지 ETF",
        "index_name": "SK하이닉스 레버리지 지수",
        "news_keywords": ["SK하이닉스 주가", "HBM 수요"],
    },
    "RISE 2차전지TOP10": {
        "site_id": "44F2", "ticker": "", "category": "국내주식",
        "keywords": ["2차전지", "배터리", "EV", "소재"],
        "description": "국내 2차전지 밸류체인 대표 10종목에 투자하는 ETF",
        "index_name": "2차전지TOP10 지수",
        "news_keywords": ["2차전지 ETF", "배터리 주식", "전기차 배터리"],
    },
    "RISE 2차전지액티브": {
        "site_id": "44C7", "ticker": "", "category": "국내주식",
        "keywords": ["2차전지", "배터리", "액티브", "EV"],
        "description": "2차전지 산업 구조적 성장 테마에 투자하는 액티브 ETF",
        "index_name": "액티브 운용 (2차전지)",
        "news_keywords": ["2차전지 액티브 ETF", "배터리 소재"],
    },
    "RISE 배터리 리사이클링": {
        "site_id": "44D7", "ticker": "", "category": "국내주식",
        "keywords": ["배터리", "리사이클링", "재활용", "2차전지"],
        "description": "EV 2차전지 배터리 재활용 산업 핵심기업에 투자하는 국내 최초 ETF",
        "index_name": "배터리 리사이클링 지수",
        "news_keywords": ["RISE 배터리 리사이클링 ETF", "배터리 재활용"],
    },
    "RISE 수소경제테마": {
        "site_id": "44A8", "ticker": "", "category": "국내주식",
        "keywords": ["수소", "친환경", "에너지", "수소경제"],
        "description": "수소 밸류체인 핵심기업에 투자하는 차세대 친환경에너지 ETF",
        "index_name": "수소경제테마 지수",
        "news_keywords": ["RISE 수소경제 ETF", "수소 밸류체인"],
    },
    "RISE 메타버스": {
        "site_id": "44C2", "ticker": "401170", "category": "국내주식",
        "keywords": ["메타버스", "게임", "콘텐츠", "XR"],
        "description": "메타버스 생태계 핵심기업에 투자하는 테마형 ETF",
        "index_name": "메타버스 지수",
        "news_keywords": ["RISE 메타버스 ETF", "메타버스 주식"],
    },
    "RISE 게임테마": {
        "site_id": "4488", "ticker": "", "category": "국내주식",
        "keywords": ["게임", "모바일게임", "콘솔", "e스포츠"],
        "description": "국내 게임 상장사에 투자하는 국내 최초 게임 테마 ETF",
        "index_name": "게임테마 지수",
        "news_keywords": ["게임 ETF", "국내 게임주"],
    },
    "RISE K엔터&여행레저": {
        "site_id": "44C8", "ticker": "", "category": "국내주식",
        "keywords": ["K엔터", "여행레저", "콘텐츠", "한류"],
        "description": "K콘텐츠·한류 엔터테인먼트 및 여행레저 기업에 투자",
        "index_name": "K엔터&여행레저 지수",
        "news_keywords": ["K엔터 ETF", "한류 콘텐츠 주식"],
    },
    "RISE 바이오TOP10액티브": {
        "site_id": "44I0", "ticker": "", "category": "국내주식",
        "keywords": ["바이오", "제약", "헬스케어", "TOP10"],
        "description": "글로벌로 나아가는 국내 제약·바이오 상위 10개 기업에 투자하는 액티브 ETF",
        "index_name": "액티브 운용 (바이오TOP10)",
        "news_keywords": ["RISE 바이오TOP10 ETF", "국내 바이오 주식"],
    },
    "RISE 헬스케어": {
        "site_id": "4450", "ticker": "", "category": "국내주식",
        "keywords": ["헬스케어", "의료기기", "제약", "바이오"],
        "description": "국내 의료기기·서비스·바이오·제약 헬스케어 기업에 투자",
        "index_name": "헬스케어 지수",
        "news_keywords": ["RISE 헬스케어 ETF", "국내 헬스케어 주식"],
    },
    "RISE 코리아전략산업액티브": {
        "site_id": "44J9", "ticker": "", "category": "국내주식",
        "keywords": ["전략산업", "방산", "조선", "반도체", "액티브"],
        "description": "국내 전략 산업 대표 기업에 투자하는 액티브 ETF",
        "index_name": "액티브 운용 (코리아전략산업)",
        "news_keywords": ["코리아전략산업 ETF", "방산 조선 반도체"],
    },
    "RISE 동학개미": {
        "site_id": "44J8", "ticker": "", "category": "국내주식",
        "keywords": ["동학개미", "국내주식", "개인투자자"],
        "description": "국내 주식 시장 재평가를 이끄는 동학개미 테마 ETF",
        "index_name": "동학개미 지수",
        "news_keywords": ["RISE 동학개미 ETF", "코스피 재평가"],
    },
    "RISE ESG사회책임투자": {
        "site_id": "4479", "ticker": "290130", "category": "국내주식",
        "keywords": ["ESG", "사회책임투자", "지속가능"],
        "description": "ESG 평가 우수 국내 기업에 투자하는 사회책임투자 ETF",
        "index_name": "ESG사회책임투자 지수",
        "news_keywords": ["RISE ESG ETF", "국내 ESG 투자"],
    },
    "RISE 5대그룹주": {
        "site_id": "4413", "ticker": "105780", "category": "국내주식",
        "keywords": ["5대그룹", "삼성", "SK", "현대차", "LG", "롯데"],
        "description": "삼성·SK·현대차·LG·롯데 5대 그룹 대표주에 투자",
        "index_name": "5대그룹주 지수",
        "news_keywords": ["5대그룹 주식", "국내 대기업 주가"],
    },
    "RISE IT플러스": {
        "site_id": "4496", "ticker": "326240", "category": "국내주식",
        "keywords": ["IT", "기술주", "반도체", "인터넷"],
        "description": "국내 IT 대표 기업에 투자하는 기술주 ETF",
        "index_name": "IT플러스 지수",
        "news_keywords": ["RISE IT플러스 ETF", "국내 IT 주식"],
    },
    "RISE 내수주플러스": {
        "site_id": "44J5", "ticker": "", "category": "국내주식",
        "keywords": ["내수주", "소비재", "유통", "음식료"],
        "description": "국내 소비 경기 회복 수혜 내수 대표 기업에 투자",
        "index_name": "내수주플러스 지수",
        "news_keywords": ["내수주 ETF", "국내 소비 경기"],
    },

    # ══════════════════════════════════════════════════
    #  국내주식 — 팩터
    # ══════════════════════════════════════════════════
    "RISE 코리아밸류업": {
        "site_id": "44H7", "ticker": "", "category": "국내주식",
        "keywords": ["밸류업", "기업가치", "ROE", "주주환원"],
        "description": "수익성·주주환원·시장가치 우수 100개 기업에 투자하는 밸류업 ETF",
        "index_name": "코리아밸류업 지수",
        "news_keywords": ["RISE 코리아밸류업 ETF", "기업 밸류업 프로그램"],
    },
    "RISE 코리아밸류업위클리고정커버드콜": {
        "site_id": "44J2", "ticker": "0094M0", "category": "국내주식",
        "keywords": ["밸류업", "커버드콜", "위클리", "월배당"],
        "description": "코리아밸류업 지수에 위클리 고정 커버드콜 전략을 더한 월분배 ETF",
        "index_name": "코리아밸류업 위클리고정커버드콜 지수",
        "news_keywords": ["RISE 밸류업 커버드콜", "월배당 ETF"],
    },
    "RISE 200위클리커버드콜": {
        "site_id": "44G3", "ticker": "475720", "category": "국내주식",
        "keywords": ["코스피200", "커버드콜", "위클리", "월배당"],
        "description": "코스피200 기반 위클리 커버드콜로 매월 분배금 지급",
        "index_name": "코스피200 위클리커버드콜 지수",
        "news_keywords": ["RISE 200위클리커버드콜", "월배당 ETF"],
    },
    "RISE V&S셀렉트밸류": {
        "site_id": "4444", "ticker": "", "category": "국내주식",
        "keywords": ["밸류", "가치주", "V&S", "저평가"],
        "description": "V&S자산운용의 가치주 선별 역량을 담은 어드바이저리 ETF",
        "index_name": "V&S셀렉트밸류 지수",
        "news_keywords": ["RISE V&S셀렉트밸류 ETF", "가치주 투자"],
    },
    "RISE 수출주": {
        "site_id": "4433", "ticker": "", "category": "국내주식",
        "keywords": ["수출주", "수출기업", "글로벌경쟁력"],
        "description": "한국 대표 수출 기업에 투자하는 ETF",
        "index_name": "수출주 지수",
        "news_keywords": ["수출주 ETF", "한국 수출 기업"],
    },
    "RISE 우량업종대표주": {
        "site_id": "4434", "ticker": "", "category": "국내주식",
        "keywords": ["우량업종", "섹터로테이션", "업종대표"],
        "description": "펀더멘털 우수 10개 업종 대표 기업에 투자하는 국내 최초 섹터로테이션 ETF",
        "index_name": "우량업종대표주 지수",
        "news_keywords": ["우량업종대표주 ETF", "국내 섹터 투자"],
    },

    # ══════════════════════════════════════════════════
    #  국내주식 — 배당
    # ══════════════════════════════════════════════════
    "RISE 대형고배당10TR": {
        "site_id": "4494", "ticker": "315960", "category": "국내주식",
        "keywords": ["고배당", "대형주", "배당", "토탈리턴"],
        "description": "전년도 현금배당수익률 기준 대형 고배당 10종목에 투자, 배당 재투자",
        "index_name": "대형고배당10TR 지수",
        "news_keywords": ["RISE 대형고배당10TR", "고배당주 투자"],
    },
    "RISE 고배당": {
        "site_id": "4454", "ticker": "", "category": "국내주식",
        "keywords": ["고배당", "배당주", "배당수익률"],
        "description": "전년도 현금배당수익률 기준 고배당 종목에 투자하는 ETF",
        "index_name": "고배당 지수",
        "news_keywords": ["RISE 고배당 ETF", "고배당주"],
    },
    "RISE 코리아금융고배당": {
        "site_id": "44H8", "ticker": "", "category": "국내주식",
        "keywords": ["금융", "고배당", "은행", "보험", "증권"],
        "description": "ROE·배당수익률·PBR 기반 우수 금융기업에 투자하는 배당 ETF",
        "index_name": "코리아금융고배당 지수",
        "news_keywords": ["코리아금융고배당 ETF", "국내 금융주 배당"],
    },
    "RISE KQ고배당": {
        "site_id": "4463", "ticker": "", "category": "국내주식",
        "keywords": ["코스닥", "고배당", "KQ", "배당주"],
        "description": "코스닥 고배당 우량 종목에 투자하는 ETF",
        "index_name": "KQ고배당 지수",
        "news_keywords": ["KQ고배당 ETF", "코스닥 고배당주"],
    },
    "RISE 중소형고배당": {
        "site_id": "4466", "ticker": "", "category": "국내주식",
        "keywords": ["중소형", "고배당", "배당주"],
        "description": "코스피 중소형 및 코스닥 고배당 우량 종목에 투자하는 ETF",
        "index_name": "중소형고배당 지수",
        "news_keywords": ["중소형고배당 ETF", "중소형 배당주"],
    },
    "RISE 200금융": {
        "site_id": "4470", "ticker": "", "category": "국내주식",
        "keywords": ["코스피200", "금융", "은행", "보험"],
        "description": "코스피200 금융 섹터 기업에 투자하는 ETF",
        "index_name": "코스피200 금융 지수",
        "news_keywords": ["RISE 200금융 ETF", "국내 금융주"],
    },
    "RISE 200고배당커버드콜ATM": {
        "site_id": "4478", "ticker": "", "category": "국내주식",
        "keywords": ["고배당", "커버드콜", "ATM", "월배당"],
        "description": "코스피200 고배당 지수에 ATM 커버드콜을 결합한 월분배 ETF",
        "index_name": "코스피200 고배당 커버드콜 지수",
        "news_keywords": ["200고배당커버드콜 ETF", "월배당 고배당"],
    },
    "RISE ESG사회책임투자": {
        "site_id": "4479", "ticker": "290130", "category": "국내주식",
        "keywords": ["ESG", "사회책임투자", "지속가능"],
        "description": "ESG 평가 우수 국내 기업에 투자하는 사회책임투자 ETF",
        "index_name": "ESG사회책임투자 지수",
        "news_keywords": ["RISE ESG ETF"],
    },
}

# ─────────────────────────────────────────
#  공통 설정
# ─────────────────────────────────────────
RISE_BASE_URL = "https://www.riseetf.co.kr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.riseetf.co.kr/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

OUTPUT_DIR = "../output"
NAV_HISTORY_DAYS = 90
NEWS_COUNT = 4
