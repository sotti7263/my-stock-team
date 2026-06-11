#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""report-pptx (PDF 컴패니언): reports/{종목명}.md 를 읽어 디자인된 PDF 리포트를 생성한다.

PowerPoint/LibreOffice 가 없는 환경에서도 PPTX와 동일한 7섹션 구성·디자인으로
PDF를 직접 렌더한다(matplotlib + 맑은 고딕). 마크다운 파싱은 build_pptx 와 공유한다.

사용법:
    python build_pdf.py <종목명|reports/종목명.md>
출력:
    reports/{종목명}.pdf
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pptx import (  # noqa: E402  (파서 재사용)
    parse_report, parse_table, parse_chart, extract_bullets, extract_source,
    guardrail_lint, DISCLAIMER,
)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import Rectangle, FancyBboxPatch  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

matplotlib.rcParams["axes.unicode_minus"] = False

# ---- 디자인 토큰 (PPTX와 동일) -------------------------------------------
KB_YELLOW = "#FFBC00"
INK = "#2B2B2B"
SUBINK = "#707070"
LINE = "#E2E2E2"
BAND = "#F5F5F3"
HEAD_BG = "#333333"
HILITE = "#FFF7E0"
WHITE = "#FFFFFF"

MALGUN = r"C:\Windows\Fonts\malgun.ttf"
MALGUN_BD = r"C:\Windows\Fonts\malgunbd.ttf"
FP = fm.FontProperties(fname=MALGUN) if os.path.exists(MALGUN) else fm.FontProperties()
FP_BD = fm.FontProperties(fname=MALGUN_BD) if os.path.exists(MALGUN_BD) else FP

# 16:9, 좌표는 0~1 분수
W_IN, H_IN = 13.333, 7.5
MX = 0.85 / W_IN          # 좌우 여백 분수 ≈ 0.064
CW = 1 - 2 * MX           # 콘텐츠 폭 분수


def new_page(pdf):
    fig = plt.figure(figsize=(W_IN, H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)
    return fig, ax


def close_page(pdf, fig):
    pdf.savefig(fig, facecolor=WHITE)
    plt.close(fig)


def rect(ax, x, y, w, h, color, ec="none", lw=0):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=ec,
                           linewidth=lw, transform=ax.transAxes, zorder=2))


def text(ax, x, y, s, size, color=INK, bold=False, ha="left", va="top"):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=size, color=color,
            fontproperties=(FP_BD if bold else FP), ha=ha, va=va, zorder=3)


def footer(ax):
    text(ax, MX, 0.045, DISCLAIMER, 8.5, SUBINK, va="center")


def title_bar(ax, title, page):
    rect(ax, MX, 0.865, 0.010, 0.062, KB_YELLOW)          # 옐로우 악센트
    text(ax, MX + 0.022, 0.896, title, 21, INK, bold=True, va="center")
    text(ax, 1 - MX, 0.896, f"{page:02d}", 11, KB_YELLOW, bold=True,
         ha="right", va="center")
    rect(ax, MX, 0.846, CW, 0.0018, LINE)                 # 구분선


def wrap(s, width):
    out = []
    for para in s.split("\n"):
        out.extend(textwrap.wrap(para, width=width) or [""])
    return out


def bullets(ax, items, x, y_top, width_frac, size=13, max_items=None,
            line_gap=0.046, wrap_chars=None):
    """불릿 목록을 위→아래로 그린다. 반환: 마지막 y."""
    if max_items and len(items) > max_items:
        items = items[:max_items]
    if len(items) >= 7:
        size = min(size, 11)
    elif len(items) >= 5:
        size = min(size, 12)
    if wrap_chars is None:
        # 폰트 크기 대비 콘텐츠 폭 기준 줄당 글자 수(보수적)
        wrap_chars = max(20, int(width_frac * W_IN / (size / 72 * 0.95)))
    y = y_top
    for it in items:
        lines = wrap(it, wrap_chars)
        text(ax, x, y, "•", size, KB_YELLOW, bold=True, va="top")
        for j, ln in enumerate(lines):
            text(ax, x + 0.018, y, ln, size, INK, va="top")
            y -= line_gap * (size / 13)
        y -= line_gap * 0.35  # 항목 간 간격
    return y


def caption(ax, x, y, sources, width_frac):
    if not sources:
        return y
    txt = "  ·  ".join(sources)
    for ln in wrap(txt, int(width_frac * W_IN / (9 / 72 * 0.95))):
        text(ax, x, y, ln, 8.5, SUBINK, va="top")
        y -= 0.030
    return y


def draw_table(ax, headers, rows, x, y_top, width_frac,
               max_rows=None, header_fs=12, body_fs=12, row_h=0.068):
    """줄무늬 표. 반환: (y_bottom, omitted)."""
    omitted = 0
    if max_rows and len(rows) > max_rows:
        omitted = len(rows) - max_rows
        rows = rows[:max_rows]
    ncols = len(headers)
    nrows = len(rows) + 1
    first_w = width_frac * 0.16
    rest_w = (width_frac - first_w) / max(ncols - 1, 1)
    col_x = [x] + [x + first_w + rest_w * i for i in range(ncols)]
    # 행 그리기 (위에서 아래로)
    for r in range(nrows):
        ry = y_top - row_h * (r + 1)
        is_head = (r == 0)
        fill = HEAD_BG if is_head else (WHITE if r % 2 == 1 else BAND)
        rect(ax, x, ry, width_frac, row_h, fill)
        cells = headers if is_head else rows[r - 1]
        for c, val in enumerate(cells):
            cx = col_x[c]
            cw = first_w if c == 0 else rest_w
            color = WHITE if is_head else INK
            if c == 0:
                text(ax, cx + 0.006, ry + row_h / 2, str(val), body_fs,
                     color, bold=is_head, va="center")
            else:
                text(ax, cx + cw - 0.008, ry + row_h / 2, str(val),
                     body_fs, color, bold=is_head, ha="right", va="center")
    return y_top - row_h * nrows, omitted


def line_chart(fig, cats, vals, x, y, w, h):
    """분수 좌표에 꺾은선 차트를 인셋으로 그린다."""
    cax = fig.add_axes([x, y, w, h])
    cax.plot(range(len(vals)), vals, color=KB_YELLOW, linewidth=2.2)
    cax.fill_between(range(len(vals)), vals, min(vals), color=KB_YELLOW, alpha=0.08)
    cax.set_facecolor(WHITE)
    for sp in ("top", "right"):
        cax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        cax.spines[sp].set_color(LINE)
    # x축 라벨 솎기
    n = len(cats)
    step = max(1, n // 7)
    ticks = list(range(0, n, step))
    cax.set_xticks(ticks)
    cax.set_xticklabels([cats[i][5:] for i in ticks], fontproperties=FP,
                        fontsize=8, color=SUBINK, rotation=0)
    for lbl in cax.get_yticklabels():
        lbl.set_fontproperties(FP)
        lbl.set_fontsize(8)
        lbl.set_color(SUBINK)
    cax.tick_params(length=0)
    cax.margins(x=0.01)


# ---- 슬라이드 렌더 --------------------------------------------------------
def page_cover(pdf, title, date):
    fig, ax = new_page(pdf)
    rect(ax, 0, 0, 0.034, 1, KB_YELLOW)               # 좌측 세로 밴드
    text(ax, MX, 0.66, "주식 리서치 리포트", 15, SUBINK, bold=True, va="center")
    text(ax, MX, 0.55, title, 40, INK, bold=True, va="center")
    rect(ax, MX, 0.46, 0.165, 0.012, KB_YELLOW)       # 옐로우 언더라인
    if date:
        text(ax, MX, 0.40, f"작성일  {date}", 13, SUBINK, va="center")
    footer(ax)
    close_page(pdf, fig)


def page_overview(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "종목 개요", page)
    bullets(ax, extract_bullets(sec), MX, 0.79, CW, size=15, max_items=8,
            line_gap=0.050)
    footer(ax)
    close_page(pdf, fig)


def page_financials(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "재무 요약 (최근 3개년)", page)
    tbl = parse_table(sec)
    y = 0.80
    if tbl:
        y, omitted = draw_table(ax, tbl[0], tbl[1], MX, y, CW,
                                max_rows=3, header_fs=13, body_fs=13)
        y = caption(ax, MX, y - 0.03, extract_source(sec), CW)
        if omitted:
            text(ax, MX, y, f"※ 최근 3개년만 표기(이전 {omitted}개 연도 생략)",
                 8.5, SUBINK, va="top")
            y -= 0.03
        bullets(ax, extract_bullets(sec), MX, y - 0.03, CW, size=12,
                max_items=4, line_gap=0.044)
    else:
        bullets(ax, extract_bullets(sec), MX, y, CW, size=13)
    footer(ax)
    close_page(pdf, fig)


def page_price(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "가격 / 추세", page)
    chart = parse_chart(sec)
    bul = extract_bullets(sec)
    if chart and len(chart[1]) >= 2:
        line_chart(fig, chart[0], chart[1], MX, 0.42, 0.55, 0.36)
        bullets(ax, bul, MX + 0.60, 0.79, CW - 0.60, size=12, max_items=6,
                line_gap=0.052)
        caption(ax, MX, 0.37, extract_source(sec), 0.55)
    else:
        tbl = parse_table(sec)
        if tbl:
            y, _ = draw_table(ax, tbl[0], tbl[1], MX, 0.80, CW, max_rows=8,
                              body_fs=11)
            y = caption(ax, MX, y - 0.03, extract_source(sec), CW)
            bullets(ax, bul, MX, y - 0.03, CW, size=11, max_items=3)
        else:
            bullets(ax, bul, MX, 0.79, CW, size=13)
    footer(ax)
    close_page(pdf, fig)


def page_news(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "뉴스 · 심리", page)
    bullets(ax, extract_bullets(sec), MX, 0.79, CW, size=13, max_items=7,
            line_gap=0.050)
    footer(ax)
    close_page(pdf, fig)


def page_risk(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "리스크", page)
    tbl = parse_table(sec)
    if tbl:
        draw_table(ax, tbl[0], tbl[1], MX, 0.80, CW, max_rows=6, body_fs=11)
    else:
        bullets(ax, extract_bullets(sec), MX, 0.79, CW, size=13, max_items=7,
                line_gap=0.050)
    footer(ax)
    close_page(pdf, fig)


def page_summary(pdf, sec, page):
    fig, ax = new_page(pdf)
    title_bar(ax, "한 줄 종합", page)
    bul = extract_bullets(sec)
    headline = bul[0] if bul else "(종합 의견 미작성)"
    rest = bul[1:]
    # 강조 박스
    box = FancyBboxPatch((MX, 0.60), CW, 0.16,
                         boxstyle="round,pad=0.004,rounding_size=0.01",
                         facecolor=HILITE, edgecolor=KB_YELLOW, linewidth=1.5,
                         transform=ax.transAxes, zorder=2)
    ax.add_patch(box)
    hl = wrap(headline, 64)
    hy = 0.685
    for ln in hl[:2]:
        text(ax, MX + 0.02, hy, ln, 17, INK, bold=True, va="center")
        hy -= 0.045
    if rest:
        bullets(ax, rest, MX, 0.55, CW, size=13, max_items=5, line_gap=0.050)
    footer(ax)
    close_page(pdf, fig)


# ---- 엔트리 --------------------------------------------------------------
def resolve_paths(arg: str):
    p = Path(arg)
    src = p if p.suffix.lower() == ".md" else Path("reports") / f"{arg}.md"
    return src, src.with_suffix(".pdf")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("사용법: python build_pdf.py <종목명|reports/종목명.md>")
        sys.exit(1)
    src, out = resolve_paths(sys.argv[1])
    if not src.exists():
        print(f"[오류] 입력 파일을 찾을 수 없습니다: {src}")
        sys.exit(1)

    md = src.read_text(encoding="utf-8")
    hits = guardrail_lint(md)
    if hits:
        print("⚠ 가드레일 경고 — 매수/매도·목표가 단정 표현 감지:")
        for ln, txt_ in hits:
            print(f"   L{ln}: {txt_}")
    else:
        print("✓ 가드레일 점검 통과")

    data = parse_report(md)
    sec = data["sections"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out) as pdf:
        page_cover(pdf, data["title"], data["date"])
        page_overview(pdf, sec.get("overview", []), 2)
        page_financials(pdf, sec.get("financials", []), 3)
        page_price(pdf, sec.get("price", []), 4)
        page_news(pdf, sec.get("news", []), 5)
        page_risk(pdf, sec.get("risk", []), 6)
        page_summary(pdf, sec.get("summary", []), 7)
    print(f"✓ 생성 완료: {out}  (7페이지)")


if __name__ == "__main__":
    main()
