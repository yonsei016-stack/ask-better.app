import streamlit as st
from openai import OpenAI
from datetime import datetime
import zipfile
import io

# =============================
# 페이지 설정
# =============================
st.set_page_config(
    page_title="文章改写 AI (3가지 버전)",
    page_icon="📝",
    layout="centered"
)

st.title("📝 AI 글 수정 도우미")
st.caption("원문 + 사용자의 선호를 입력하면, 서로 다른 3가지 수정 버전을 생성하고 다운로드할 수 있습니다.")

# =============================
# 사이드바: API 설정
# =============================
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

    model = st.selectbox(
        "모델 선택",
        options=["gpt-5-mini", "gpt-5.2"],
        index=0
    )

    output_language = st.selectbox(
        "출력 언어",
        ["한국어", "中文", "English"],
        index=0
    )

# =============================
# 원문 입력
# =============================
st.subheader("1️⃣ 원문 입력")
source_text = st.text_area(
    "수정하고 싶은 원문을 입력하세요:",
    height=240,
    placeholder="과제 글, 보고서, 에세이 초안 등을 붙여 넣으세요."
)

# =============================
# 사용자 선호 입력
# =============================
st.subheader("2️⃣ 사용자 선호 설정")

col1, col2 = st.columns(2)

with col1:
    purpose = st.selectbox(
        "글의 목적",
        ["과제/보고서", "설명/요약", "지원서/동기문", "정리/회고", "이메일", "기타"]
    )
    audience = st.selectbox(
        "대상 독자",
        ["교수/평가자", "일반 독자", "전공자", "직장/업무", "불특정"]
    )
    tone = st.selectbox(
        "문체/톤",
        ["중립적이고 명확하게", "더 공식적으로", "자연스럽고 부드럽게", "학술적으로", "설득력 있게"]
    )

with col2:
    length = st.selectbox(
        "글 길이",
        ["짧게", "보통", "조금 길게"]
    )
    structure = st.selectbox(
        "구조",
        ["자유 형식", "문단 구분 명확히", "요점 + 설명", "서론-본론-결론"]
    )
    creativity = st.selectbox(
        "수정 강도",
        ["낮음 (보수적)", "중간", "높음 (더 적극적)"]
    )

style_keywords = st.text_input(
    "원하는 스타일 키워드 (선택)",
    placeholder="예: 논리적, 간결, 대학 과제 느낌, 과장 금지"
)

must_include = st.text_area(
    "반드시 포함할 내용 (선택)",
    height=80
)

must_avoid = st.text_area(
    "포함하지 말아야 할 내용 (선택)",
    height=80
)

# =============================
# 언어 지시
# =============================
def language_instruction(lang):
    if lang == "한국어":
        return "한국어로 작성해줘."
    if lang == "中文":
        return "请用中文输出。"
    return "Output in English."

# =============================
# 사용자 선호 요약
# =============================
def build_preferences():
    prefs = [
        f"글의 목적: {purpose}",
        f"대상 독자: {audience}",
        f"문체: {tone}",
        f"길이: {length}",
        f"구조: {structure}",
        f"수정 강도: {creativity}",
    ]
    if style_keywords.strip():
        prefs.append(f"스타일 키워드: {style_keywords}")
    if must_include.strip():
        prefs.append(f"반드시 포함: {must_include}")
    if must_avoid.strip():
        prefs.append(f"금지 사항: {must_avoid}")

    prefs.append(language_instruction(output_language))
    return "\n".join(f"- {p}" for p in prefs)

# =============================
# 버전별 지시
# =============================
def version_instruction(v):
    if v == "A":
        return "버전 A: 원문 의미를 최대한 유지하며 구조와 표현만 다듬어줘."
    if v == "B":
        return "버전 B: 논리와 설득력을 강화하여 더 잘 쓴 글처럼 수정해줘."
    return "버전 C: 자연스럽고 읽기 쉬운 완성본처럼 수정해줘."

# =============================
# OpenAI 호출
# =============================
def generate_versions(client, model_name, text, prefs):
    system_msg = (
        "너는 전문 글 수정 AI야. "
        "사실을 추가하거나 왜곡하지 말고, 요청된 조건에 맞춰 글을 수정해. "
        "결과는 수정된 글 본문만 출력해."
    )

    results = {}
    for v in ["A", "B", "C"]:
        user_msg = f"""
[원문]
{text}

[사용자 선호]
{prefs}

[수정 지침]
{version_instruction(v)}

수정된 글만 출력해.
"""
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.6 if creativity.startswith("높음") else 0.3
        )
        results[v] = response.choices[0].message.content.strip()
    return results

# =============================
# 실행 버튼
# =============================
st.divider()
run = st.button("🚀 3가지 수정 버전 생성", use_container_width=True)

if "results" not in st.session_state:
    st.session_state["results"] = {}

if run:
    if not source_text.strip():
        st.warning("원문을 입력해 주세요.")
    elif not api_key.strip():
        st.error("OpenAI API Key를 입력해 주세요.")
    else:
        try:
            client = OpenAI(api_key=api_key)
            prefs = build_preferences()
            with st.spinner("AI가 글을 수정 중입니다..."):
                st.session_state["results"] = generate_versions(
                    client, model, source_text, prefs
                )
            st.success("완료되었습니다!")
        except Exception as e:
            st.error("오류가 발생했습니다.")
            st.code(str(e))

# =============================
# 결과 표시 및 다운로드
# =============================
results = st.session_state.get("results", {})

def zip_files(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()

if results:
    st.subheader("3️⃣ 수정 결과")

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"article_revision_{now}"

    tabs = st.tabs(["버전 A", "버전 B", "버전 C"])

    for tab, key in zip(tabs, ["A", "B", "C"]):
        with tab:
            text = results[key]
            st.text_area("수정된 글", value=text, height=320)
            st.download_button(
                "⬇️ 다운로드 (.txt)",
                data=text.encode("utf-8"),
                file_name=f"{base}_{key}.txt",
                mime="text/plain"
            )

    zip_data = zip_files({
        f"{base}_A.txt": results["A"],
        f"{base}_B.txt": results["B"],
        f"{base}_C.txt": results["C"],
    })

    st.download_button(
        "📦 3가지 버전 ZIP 다운로드",
        data=zip_data,
        file_name=f"{base}_ALL.zip",
        mime="application/zip",
        use_container_width=True
    )
else:
    st.info("아직 결과가 없습니다. 원문과 설정을 입력한 뒤 실행해 주세요.")
