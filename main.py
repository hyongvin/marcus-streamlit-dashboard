import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import re
from collections import Counter
import math

st.set_page_config(page_title="마커스 성장 분석 대시보드", layout="wide")

st.title("🚀 마커스 경쟁사 분석 분석 대시보드")

# =========================
# 1) 리뷰 데이터 로딩
# =========================
def load_reviews(path):
    for enc in ["cp949", "euc-kr", "utf-8-sig", "utf-8"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"지원 인코딩으로 읽을 수 없는 파일입니다: {path}")

df_moqous  = load_reviews("data\moqous_reviews.csv")
df_titicaca = load_reviews("data\titicaca_reviews.csv")
df_autech   = load_reviews("data\autech_reviews.csv")

TEXT_COL = "review_text"   # 전체에서 공통으로 사용할 컬럼명

# =========================
# 2) 공통 함수들
# =========================
def get_rating_dist(df, brand_name):
    ratings = df["rating"].round().astype(int)
    counts = ratings.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    total = counts.sum()
    dist_df = pd.DataFrame({
        "브랜드": brand_name,
        "점수": counts.index,
        "개수": counts.values,
        "비율(%)": (counts.values / total * 100).round(1)
    })
    return dist_df

def tokenize_korean(text):
    """간단 한글 토크나이저: 2글자 이상 한글만 추출 + 불용어 제거"""
    tokens = re.findall(r"[가-힣]{2,}", str(text))
    stopwords = {"정말", "너무", "그리고", "하지만", "그래서", "그냥", "이번", "제품", "자전거"}
    return [t for t in tokens if t not in stopwords]

def top_keywords_by_rating(df, brand_name, top_n=3):
    """별점(1~5)별 상위 키워드 top_n 추출"""
    ratings = df["rating"].round().astype(int)
    results = []

    for r in sorted(ratings.unique()):
        sub = df[ratings == r]
        all_tokens = []
        for txt in sub[TEXT_COL].dropna():
            all_tokens.extend(tokenize_korean(txt))

        counter = Counter(all_tokens)
        for kw, cnt in counter.most_common(top_n):
            results.append({
                "브랜드": brand_name,
                "별점": int(r),
                "키워드": kw,
                "빈도": int(cnt)
            })

    return pd.DataFrame(results)

PAGE_SIZE = 5

def show_reviews_with_pagination(df_reviews, key_prefix: str):
    """
    df_reviews : 이미 '선택한 별점 + 선택한 키워드'로 필터된 DataFrame
    key_prefix : 브랜드 구분용 키 (예: "titicaca", "autec_5star")
    """
    total = len(df_reviews)
    if total == 0:
        st.info("조건에 맞는 리뷰가 없습니다.")
        return

    page_key = f"page_{key_prefix}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    max_page = math.ceil(total / PAGE_SIZE) - 1
    page = st.session_state[page_key]

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("◀ 이전", disabled=(page == 0), key=f"prev_{key_prefix}"):
            st.session_state[page_key] = max(page - 1, 0)

    with col3:
        if st.button("다음 ▶", disabled=(page >= max_page), key=f"next_{key_prefix}"):
            st.session_state[page_key] = min(page + 1, max_page)

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current = df_reviews.iloc[start:end]

    st.caption(f"총 {total}개 중 {start+1}–{min(end, total)}개 표시 중")

    for i, txt in enumerate(current["리뷰텍스트"], start=start + 1):
        st.markdown(f"**({i})** {txt}")

def fmt_row(group):
    items = [f"{row['키워드']}({row['빈도']})" for _, row in group.iterrows()]
    return " / ".join(items)

# =========================
# 탭 2만 남기기
# =========================
tab2, = st.tabs(["⭐ 시장 리뷰 비교"])

with tab2:
    st.title("⭐시장 경쟁 브랜드 리뷰 비교")

    st.subheader("1️⃣ 브랜드별 평균 별점 & 리뷰 수 비교")

    summary = pd.DataFrame({
        "브랜드": ["마커스", "티티카카", "오텍"],
        "리뷰 수": [
            len(df_moqous),
            len(df_titicaca),
            len(df_autech)
        ],
        "평균 별점": [
            df_moqous["rating"].mean(),
            df_titicaca["rating"].mean(),
            df_autech["rating"].mean()
        ]
    })

    st.dataframe(summary.style.format({"평균 별점": "{:.2f}"}), use_container_width=True)

    st.subheader("2️⃣ 평균 별점 시각화")

    chart_rating = (
        alt.Chart(summary)
        .mark_bar()
        .encode(
            x=alt.X("브랜드:N", title="브랜드"),
            y=alt.Y("평균 별점:Q", title="평균 별점", scale=alt.Scale(domain=[0, 5])),
            color="브랜드:N",
            tooltip=["브랜드", "리뷰 수", alt.Tooltip("평균 별점:Q", format=".2f")]
        )
        .properties(height=350)
    )

    st.altair_chart(chart_rating, use_container_width=True)

    st.subheader("3️⃣ 별점 분포 (1점~5점 개수 및 비율)")

    dist_moq   = get_rating_dist(df_moqous,  "마커스")
    dist_aute  = get_rating_dist(df_autech,  "오텍(전기자전거)")
    dist_titi  = get_rating_dist(df_titicaca,"티티카카(전통자전거)")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        st.markdown("**마커스**")
        st.table(
            dist_moq[["점수", "개수", "비율(%)"]]
            .sort_values("점수")
            .set_index("점수")
        )

    with col_d2:
        st.markdown("**오텍(전기 자전거)**")
        st.table(
            dist_aute[["점수", "개수", "비율(%)"]]
            .sort_values("점수")
            .set_index("점수")
        )

    with col_d3:
        st.markdown("**티티카카(전통 자전거)**")
        st.table(
            dist_titi[["점수", "개수", "비율(%)"]]
            .sort_values("점수")
            .set_index("점수")
        )

    # -------------------------
    # 전통 자전거 (티티카카)
    # -------------------------
    st.subheader("전통 자전거")
    st.subheader("4️⃣ 레이팅별 키워드 분석 (티티카카 기준)")

    titi_kw_by_rating = top_keywords_by_rating(df_titicaca, "티티카카", top_n=3)

    st.markdown("**티티카카 별점별 상위 3개 키워드 요약**")

    titi_top3 = (
        titi_kw_by_rating
        .sort_values(["별점", "빈도"], ascending=[True, False])
        .groupby("별점")
        .head(3)
    )

    summary_table_titi = (
        titi_top3
        .groupby("별점")
        .apply(fmt_row)
        .reset_index()
        .sort_values("별점")
    )
    summary_table_titi.rename(columns={"별점": "별점(★)"}, inplace=True)

    st.table(summary_table_titi)

    selected_rating_titi = st.selectbox(
        "별점 선택 (티티카카 기준)",
        sorted(titi_kw_by_rating["별점"].unique()),
        key="titi_rating_sel"
    )

    titi_kw_selected = titi_kw_by_rating[
        titi_kw_by_rating["별점"] == selected_rating_titi
    ]

    chart_titi_kw = (
        alt.Chart(titi_kw_selected)
        .mark_bar()
        .encode(
            x=alt.X("키워드:N", title=f"{selected_rating_titi}점 리뷰에서 상위 키워드"),
            y=alt.Y("빈도:Q", title="등장 빈도(건수)"),
            tooltip=["키워드", "빈도"]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_titi_kw, use_container_width=True)

    st.markdown("**선택한 별점에서 특정 키워드가 들어간 리뷰 예시 (티티카카)**")

    selected_kw_titi = st.selectbox(
        "키워드 선택",
        titi_kw_selected["키워드"].tolist(),
        key="titi_kw_sel"
    )

    ex_reviews_titi_df = df_titicaca[
        (df_titicaca["rating"].round().astype(int) == selected_rating_titi) &
        (df_titicaca[TEXT_COL].str.contains(selected_kw_titi, na=False))
    ][[TEXT_COL]].rename(columns={TEXT_COL: "리뷰텍스트"})

    show_reviews_with_pagination(
        ex_reviews_titi_df,
        key_prefix=f"titicaca_{selected_rating_titi}_{selected_kw_titi}"
    )

    # -------------------------
    # 전기 자전거 (오텍)
    # -------------------------
    st.subheader("전기 자전거")
    st.subheader("5️⃣ 레이팅별 키워드 분석 (오텍 기준)")

    aute_kw_by_rating = top_keywords_by_rating(df_autech, "오텍", top_n=3)

    st.markdown("**오텍 별점별 상위 3개 키워드 요약**")

    aute_top3 = (
        aute_kw_by_rating
        .sort_values(["별점", "빈도"], ascending=[True, False])
        .groupby("별점")
        .head(3)
    )

    summary_table_aute = (
        aute_top3
        .groupby("별점")
        .apply(fmt_row)
        .reset_index()
        .sort_values("별점")
    )
    summary_table_aute.rename(columns={"별점": "별점(★)"}, inplace=True)

    st.table(summary_table_aute)

    selected_rating_aute = st.selectbox(
        "별점 선택 (오텍 기준)",
        sorted(aute_kw_by_rating["별점"].unique()),
        key="aute_rating_kw"
    )

    aute_kw_selected = aute_kw_by_rating[
        aute_kw_by_rating["별점"] == selected_rating_aute
    ]

    chart_aute_kw = (
        alt.Chart(aute_kw_selected)
        .mark_bar()
        .encode(
            x=alt.X("키워드:N", title=f"{selected_rating_aute}점 리뷰에서 상위 키워드"),
            y=alt.Y("빈도:Q", title="등장 빈도(건수)"),
            tooltip=["키워드", "빈도"]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_aute_kw, use_container_width=True)

    st.markdown("**선택한 별점에서 특정 키워드가 들어간 리뷰 예시 (오텍)**")

    selected_kw_aute = st.selectbox(
        "키워드 선택",
        aute_kw_selected["키워드"].tolist(),
        key="aute_kw_example"
    )

    ex_reviews_aute_df = df_autech[
        (df_autech["rating"].round().astype(int) == selected_rating_aute) &
        (df_autech[TEXT_COL].str.contains(selected_kw_aute, na=False))
    ][[TEXT_COL]].rename(columns={TEXT_COL: "리뷰텍스트"})

    show_reviews_with_pagination(
        ex_reviews_aute_df,
        key_prefix=f"aute_{selected_rating_aute}_{selected_kw_aute}"
    )

    # -------------------------
    # 마커스
    # -------------------------
    st.subheader("6️⃣ 레이팅별 키워드 분석 (마커스 기준)")

    marcus_kw_by_rating = top_keywords_by_rating(df_moqous, "마커스", top_n=3)

    st.markdown("**마커스 별점별 상위 3개 키워드 요약**")

    marcus_top3 = (
        marcus_kw_by_rating
        .sort_values(["별점", "빈도"], ascending=[True, False])
        .groupby("별점")
        .head(3)
    )

    summary_table_marcus = (
        marcus_top3
        .groupby("별점")
        .apply(fmt_row)
        .reset_index()
        .sort_values("별점")
    )
    summary_table_marcus.rename(columns={"별점": "별점(★)"}, inplace=True)

    st.table(summary_table_marcus)

    selected_rating_marcus = st.selectbox(
        "별점 선택 (마커스 기준)",
        sorted(marcus_kw_by_rating["별점"].unique()),
        key="marcus_rating_sel"
    )

    marcus_kw_selected = marcus_kw_by_rating[
        marcus_kw_by_rating["별점"] == selected_rating_marcus
    ]

    chart_marcus_kw = (
        alt.Chart(marcus_kw_selected)
        .mark_bar()
        .encode(
            x=alt.X("키워드:N", title=f"{selected_rating_marcus}점 리뷰에서 상위 키워드"),
            y=alt.Y("빈도:Q", title="등장 빈도(건수)"),
            tooltip=["키워드", "빈도"]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_marcus_kw, use_container_width=True)

    st.markdown("**선택한 별점에서 특정 키워드가 들어간 리뷰 예시 (마커스)**")

    selected_kw_marcus = st.selectbox(
        "키워드 선택",
        marcus_kw_selected["키워드"].tolist(),
        key="marcus_kw_sel"
    )

    ex_reviews_marcus_df = df_moqous[
        (df_moqous["rating"].round().astype(int) == selected_rating_marcus) &
        (df_moqous[TEXT_COL].str.contains(selected_kw_marcus, na=False))
    ][[TEXT_COL]].rename(columns={TEXT_COL: "리뷰텍스트"})

    show_reviews_with_pagination(
        ex_reviews_marcus_df,
        key_prefix=f"marcus_{selected_rating_marcus}_{selected_kw_marcus}"
    )

