# app.py
# Streamlit 앱: Ask better
# - 사용자의 한 줄 질문을 더 좋은 질문으로 개선 (3개 제안)
# - 사용자의 취향(톤/목적)에 따라 문장 스타일 반영
# - 3개 중 하나 선택 후 “복사하기” 버튼으로 클립보드 복사

import os
import json
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

st.set_page_config(page_title="Ask better", page_icon="🧠", layout="centered")

st.title("🧠 Ask better")
st.caption("사용자의 질문을 더 좋은 질문으로 바꿔주는 AI 도우미")

# --- API 키 입력 ---
st.subheader("🔑 OpenAI API 키 입력")
api_key = st.text_input(
    "OpenAI API 키를 입력하세요",
    type="password",
    placeholder="sk-..."
)

if not api_key:
    st.info("API 키를 입력하면 앱을 사용할 수 있습니다.")
    st.stop()

client = OpenAI(api_key=api_key)


# --- 사용자 취향(기능 2) ---
st.subheader("1) 질문 입력")
user_question = st.text_input("질문을 한 줄로 입력하세요", placeholder="예) 이 주제에 대해 설명해줘")

st.subheader("2) 사용자 취향 선택")
tone = st.selectbox("말투(톤)", ["공손하게", "친근하게", "간결하게", "전문적으로"])
purpose = st.selectbox("질문 목적", ["정보수집", "논리적 사고", "문제풀이", "창작"])

st.divider()

# --- 핵심 기능 1: 질문 개선하기 ---
def build_prompt(q: str, tone_choice: str, purpose_choice: str) -> str:
    return f"""
너는 '질문 개선' 전문가다.
사용자가 입력한 질문을 ChatGPT에게 묻기 좋은 질문으로 바꿔줘.

요구사항:
- 반드시 개선된 질문 3개를 제안할 것
- 각 질문은 서로 조금씩 다른 방향(범위/조건/맥락/요구 산출물)을 갖게 할 것
- 사용자의 취향을 반영할 것:
  - 말투(톤): {tone_choice}
  - 목적: {purpose_choice}
- 원문 질문의 의미를 왜곡하지 말 것
- 불필요한 장황한 설명은 금지 (질문 문장만 제시)
- 출력은 반드시 JSON만:
  {{
    "questions": ["...", "...", "..."]
  }}

사용자 질문:
{q}
""".strip()

def generate_better_questions(q: str, tone_choice: str, purpose_choice: str):
    prompt = build_prompt(q, tone_choice, purpose_choice)

    response = client.responses.create(
        model="gpt-5.2",
        input=prompt,
    )

    text = (response.output_text or "").strip()

    # JSON 파싱 (실패 시 최소 복구)
    try:
        data = json.loads(text)
        qs = data.get("questions", [])
        qs = [str(x).strip() for x in qs if str(x).strip()]
    except Exception:
        # JSON이 깨졌을 때: 줄 단위로 3개까지 복구
        lines = [ln.strip("-• \t") for ln in text.splitlines() if ln.strip()]
        qs = lines[:3]

    # 항상 3개를 맞추기(부족하면 원문 기반 보강) — 기능 추가가 아니라 출력 안정화
    while len(qs) < 3:
        qs.append(f"{q} (추가로 어떤 조건/범위를 포함해야 하나요?)")

    return qs[:3]

# --- UI: 버튼 ---
if "candidates" not in st.session_state:
    st.session_state.candidates = None
if "selected" not in st.session_state:
    st.session_state.selected = None

if st.button("질문 개선하기", type="primary", use_container_width=True):
    if not user_question.strip():
        st.error("질문을 입력해 주세요.")
    else:
        with st.spinner("질문을 개선하는 중..."):
            st.session_state.candidates = generate_better_questions(user_question.strip(), tone, purpose)
            st.session_state.selected = st.session_state.candidates[0]

# --- 결과 화면 ---
if st.session_state.candidates:
    st.subheader("결과: 개선된 질문 선택 (3개 중)")
    st.session_state.selected = st.radio(
        "아래에서 하나를 선택하세요",
        options=st.session_state.candidates,
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("선택한 질문:")
    st.code(st.session_state.selected, language="")

    # --- 복사하기 버튼 (클립보드) ---
    if st.button("복사하기", use_container_width=True):
        safe_text = st.session_state.selected.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        components.html(
            f"""
            <script>
            const text = `{safe_text}`;
            navigator.clipboard.writeText(text).then(() => {{
                const el = document.createElement('div');
                el.innerText = "클립보드에 복사되었습니다.";
                el.style.fontFamily = "sans-serif";
                el.style.padding = "8px 0";
                document.body.appendChild(el);
            }});
            </script>
            """,
            height=40,
        )

