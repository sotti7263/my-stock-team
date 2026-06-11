---
description: 완성된 reports/{종목}.md 를 디자인된 PPTX/PDF 리포트로 내보냅니다 (report-pptx 스킬)
argument-hint: <종목명>
allowed-tools: ["Bash", "Read"]
---

`reports/$ARGUMENTS.md` 를 디자인된 리포트로 내보냅니다. 번들 스크립트는 `${CLAUDE_PLUGIN_ROOT}` 로 참조합니다.

## 절차
1. `reports/$ARGUMENTS.md` 가 있는지 확인합니다. 없으면 먼저 `/stock-research $ARGUMENTS` 로 작성하라고 안내합니다.
2. 의존성 확인: `python-pptx`(PPTX), `matplotlib`(PDF). 없으면 `pip install python-pptx matplotlib`.
3. 다음을 실행합니다.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/report-pptx/build_pptx.py" "$ARGUMENTS"
python "${CLAUDE_PLUGIN_ROOT}/skills/report-pptx/build_pdf.py" "$ARGUMENTS"
```

4. 생성 결과(`reports/$ARGUMENTS.pptx`, `reports/$ARGUMENTS.pdf`)와 콘솔의 **가드레일 점검 결과**를 사용자에게 보고합니다. 가드레일 경고가 있으면 `.md` 를 수정하도록 안내합니다.

## 디자인 규칙 (스킬에 내장)
- 7섹션 고정: 표지 → 종목 개요 → 재무 요약(3개년 표) → 가격/추세(차트) → 뉴스·심리 → 리스크 → 한 줄 종합
- 포인트색 KB 옐로우 `#FFBC00` + 그레이/화이트, 한글 폰트 **맑은 고딕** 고정
- 표 오버플로 방지(행 수 자동 제한), 표 아래 출처 캡션, 매수/매도·목표가 단정 표현 린트 경고
