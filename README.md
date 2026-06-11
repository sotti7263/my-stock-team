# my-stock-team

종목명을 입력하면 **여러 애널리스트 서브에이전트가 협업**해 가치투자 관점의 리서치를 수행하고,
**검증 애널리스트**의 품질 점검을 거쳐 **디자인된 PPTX/PDF 리포트**로 내보내는 Claude Code 플러그인입니다.

## 구성

```
my-stock-team/
├── .claude-plugin/
│   ├── plugin.json          # 플러그인 매니페스트 (name: my-stock-team, v1.0.0)
│   └── marketplace.json     # 설치 카탈로그
├── agents/                  # 서브에이전트 5종
│   ├── fundamental-analyst.md         # 재무·공시 (DART, 한국)
│   ├── market-technical-analyst.md    # 가격·추세 (FinanceDataReader, 한·미)
│   ├── news-sentiment-analyst.md      # 뉴스·심리 (웹서치, 한·미)
│   ├── risk-manager-synthesizer.md    # 리스크 종합·리드 (pykrx)
│   └── report-qa-validator.md         # 검증(품질 점검) 게이트
├── skills/
│   └── report-pptx/         # 리포트 → PPTX/PDF 생성 스킬
│       ├── SKILL.md
│       ├── build_pptx.py
│       └── build_pdf.py
└── commands/
    ├── stock-research.md    # /stock-research <종목>  — 전체 파이프라인
    └── export-report.md     # /export-report <종목>   — PPTX/PDF 내보내기
```

## 설치 (마켓플레이스)

```
/plugin marketplace add <이 저장소 경로 또는 git URL>
/plugin install my-stock-team@my-stock-team
```

## 사용

```
/stock-research 삼성물산      # 데이터 수집 → 협업 → 리스크 종합 → 검증 → reports/삼성물산.md
/export-report 삼성물산        # reports/삼성물산.md → .pptx / .pdf
```

## 사전 준비

- **DART API 키**: 한국 종목 재무 분석에 필요합니다. 프로젝트 루트에 `.env` 를 만들고 본인 키를 넣으세요.
  `.env.example` 를 복사해 사용합니다. **키 값은 이 플러그인에 포함되어 있지 않습니다.**
  ```
  cp .env.example .env   # 그리고 DART_KEY 에 본인 키 입력
  ```
  DART 키 발급: https://opendart.fss.or.kr/
- **파이썬 의존성**: `pip install python-pptx matplotlib`
- 가격 데이터(FinanceDataReader)·유동성(pykrx)·뉴스(웹서치)는 키가 필요 없습니다.

## 가드레일 (모든 리포트 공통)
- 모든 수치에 `(출처: 데이터명, 연도/날짜)` 표기, 출처 없는 수치 금지
- 데이터 미확보 시 "확인 불가", 출처 없는 뉴스·루머는 "미확인"
- 매수/매도/보유·목표가·비중 단정 금지 — 판단 근거 정리까지만, 최종 판단은 사람
- 첫머리 "무료 공개 데이터 기반 학습용" 한 줄 + 끝에 데이터 출처·기준일 목록

본 플러그인의 산출물은 학습용 분석이며 투자 권유가 아닙니다.
