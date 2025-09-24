import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import datetime
import json
# app.py 상단에 이 import 구문을 추가하세요
#from jaw_analyzer import jaw_analyzer_component
# AR 화면 표시 여부 상태값 초기화
import streamlit.components.v1 as components 
if "show_ar" not in st.session_state:
    st.session_state.show_ar = False

# 토글 버튼
if st.button("개구량측정 보기/숨기기"):
    st.session_state.show_ar = not st.session_state.show_ar

# index.html 읽기
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# 상태값이 True일 때만 AR 화면 표시
if st.session_state.show_ar:
    components.html(html_content, height=1400, scrolling=False)


diagnosis_keys = {
    "muscle_pressure_2s_value": "선택 안 함",
    "muscle_referred_pain_value": "선택 안 함",
    "muscle_referred_remote_pain_value": "선택 안 함", 
    "tmj_press_pain_value": "선택 안 함",
    "headache_temples_value": "선택 안 함",
    "headache_with_jaw_value": "선택 안 함",
    "headache_reproduce_by_pressure_value": "선택 안 함",
    "headache_not_elsewhere_value": "선택 안 함",
    "crepitus_confirmed_value": "선택 안 함",
    "mao_fits_3fingers_value": "선택 안 함",
    "jaw_locked_now_value": "선택 안 함",
    "tmj_sound_value": "선택 안 함"
}
###

if 'step' not in st.session_state:
    st.session_state.step = 0
    st.session_state.validation_errors = {}

for key, default in diagnosis_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default



##

total_steps = 20
final_step = total_steps - 1


# diagnosis_keys 를 session_state 에 심는 루프
for key, default in diagnosis_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default


# STEP 13 전용 키명, DEFAULT 값도 한 번만
DATA_KEY = "neck_shoulder_symptoms"
DEFAULT_SYMPTOMS = {
    "목 통증": False,
    "어깨 통증": False,
    "뻣뻣함(강직감)": False,
    "없음": False,
    "눈 통증": False,
    "코 통증": False,
    "목구멍 통증": False,
}
st.session_state.setdefault(DATA_KEY, DEFAULT_SYMPTOMS.copy())

# 추가 증상 항목도 한 번만 초기화
ADD_KEY = "additional_symptoms"
DEFAULT_ADDS = {"눈 통증": False, "코 통증": False, "목구멍 통증": False}
st.session_state.setdefault(ADD_KEY, DEFAULT_ADDS.copy())


# ─── 1) LocalStorage Stub (서버 메모리) ──────────────────────────
class LocalStorage:
    def __init__(self):
        self._store = {}

    def setItem(self, key, value):
        self._store[key] = value

    def getItem(self, key):
        return self._store.get(key)

    def deleteItem(self, key):
        return self._store.pop(key, None)
# ────────────────────────────────────────────────────────────────

# 이제 아래부터 로컬 저장/로드 함수가 문제없이 작동합니다
localS = LocalStorage()

def load_session():
    raw = localS.getItem("jaw_analysis_session")
    if not raw or raw == "null":
        return False
    data = json.loads(raw)
    # birthdate 복원 등
    if "birthdate" in data and isinstance(data["birthdate"], str):
        try:
            data["birthdate"] = datetime.datetime.strptime(
                data["birthdate"], "%Y-%m-%d"
            ).date()
        except:
            pass
    st.session_state.update(data)
    return True

# ← 여기에 빠트리기 쉬운 콜백 함수를 정의합니다!
def sync_widget_key_with_auto_save(widget_key, target_key):
    """위젯 값을 st.session_state에 동기화하고 즉시 로컬 저장"""
    if widget_key in st.session_state:
        st.session_state[target_key] = st.session_state[widget_key]
        save_session()

def sync_time_widget_with_auto_save(time_key):
    widget_key = f"time_{time_key}_widget"
    state_key  = f"time_{time_key}"
    if widget_key in st.session_state:
        st.session_state[state_key] = st.session_state[widget_key]
        save_session()

def handle_headache_change():
    st.session_state["has_headache_now"] = st.session_state.get("has_headache_widget")
    if st.session_state["has_headache_widget"] != "예":
        for k in [
            "headache_areas", "headache_severity", "headache_frequency",
            "headache_triggers", "headache_reliefs"
        ]:
            st.session_state.pop(k, None)
    save_session()

def delete_session():
    """
    localStorage에서 저장된 세션 데이터 삭제
    """
    try:
        localS.deleteItem('jaw_analysis_session')
        return True
    except Exception as e:
        st.error(f"세션 삭제 중 오류가 발생했습니다: {str(e)}")
        return False

def has_saved_session():
    """
    저장된 세션 데이터가 있는지 확인
    """
    try:
        json_data = localS.getItem('jaw_analysis_session')
        return json_data is not None and json_data != "null"
    except:
        return False

def save_session():
    """
    현재 st.session_state의 내용을 localStorage에 저장
    """
    try:
        session_data = dict(st.session_state)

        # 날짜 → ISO 문자열
        for k, v in session_data.items():
            if isinstance(v, datetime.date):
                session_data[k] = v.strftime("%Y-%m-%d")

        # json.dumps에 default=str 옵션 추가
        json_data = json.dumps(
            session_data,
            ensure_ascii=False,
            default=str
        )
        localS.setItem("jaw_analysis_session", json_data)
        return True

    except Exception as e:
        st.error(f"세션 저장 중 오류가 발생했습니다: {e}")
        return False




from io import BytesIO
import fitz # PyMuPDF
import streamlit as st
import os

# 현재 스크립트 파일의 디렉토리를 얻습니다.
# 이렇게 하면 앱이 어디에 있든 올바른 경로를 찾을 수 있습니다.
script_dir = os.path.dirname(os.path.abspath(__file__))

# 폰트 파일의 상대 경로를 지정합니다.
# 예를 들어, NanumGothic.ttf가 app.py와 같은 폴더에 있을 경우:
FONT_FILE = os.path.join(script_dir, "NanumGothic.ttf")

# 폰트 파일이 fonts 폴더 안에 있을 경우:
# FONT_FILE = os.path.join(script_dir, "fonts", "NanumGothic.ttf")

from io import BytesIO
import fitz  # PyMuPDF
import streamlit as st
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(script_dir, "NanumGothic.ttf")

def generate_filled_pdf():
    template_path = "template5.pdf"
    doc = fitz.open(template_path)

    # neck_shoulder_symptoms 변환 (dict일 때만)
    neck_val = st.session_state.get("neck_shoulder_symptoms", {})
    if isinstance(neck_val, dict):
        neck_list = [k for k, v in neck_val.items() if v]
        st.session_state["neck_shoulder_symptoms"] = ", ".join(neck_list) if neck_list else "없음"

    # additional_symptoms 변환 (dict일 때만)
    add_val = st.session_state.get("additional_symptoms", {})
    if isinstance(add_val, dict):
        add_list = [k for k, v in add_val.items() if v]
        st.session_state["additional_symptoms"] = ", ".join(add_list) if add_list else "없음"

    # ✅ 두통 관련 리스트를 문자열로 변환
    for k in ["headache_areas", "headache_triggers", "headache_reliefs","headache_frequency"]:
        v = st.session_state.get(k, [])
        if isinstance(v, list):
            st.session_state[k] = ", ".join(v)

    # ✅ 귀 관련 선택도 문자열로 변환
    v = st.session_state.get("selected_ear_symptoms", [])
    if isinstance(v, list):
        st.session_state["selected_ear_symptoms"] = ", ".join(v)
    


    keys = [
        "name", "birthdate", "gender", "email", "address", "phone",
        "occupation", "visit_reason", "chief_complaint", "chief_complaint_other",
        "onset", "jaw_aggravation", "pain_quality", "pain_quality_other",
        "muscle_movement_pain_value", "muscle_pressure_2s_value",
        "muscle_referred_pain_value", "muscle_referred_remote_pain_value",
        "tmj_movement_pain_value","tmj_press_pain_value","headache_temples_value",
        "headache_reproduce_by_pressure_value","headache_with_jaw_value","headache_not_elsewhere_value",
        "tmj_sound_value","tmj_click_summary","crepitus_confirmed_value","jaw_locked_now_value",
        "jaw_unlock_possible_value","jaw_locked_past_value","mao_fits_3fingers_value",
        "frequency_choice","pain_level","selected_times",
        "has_headache_now","headache_areas","headache_severity","headache_frequency",
        "headache_triggers","headache_reliefs","habit_summary","additional_habits",
        "active_opening","active_pain","passive_opening","passive_pain",
        "deviation","deviation2","deflection","protrusion","protrusion_pain",
        "latero_right","latero_right_pain","latero_left","latero_left_pain",
        "occlusion","occlusion_shift",
        "tmj_noise_right_open","tmj_noise_left_open","tmj_noise_right_close","tmj_noise_left_close",
        "palpation_temporalis","palpation_medial_pterygoid","palpation_lateral_pterygoid","pain_mapping",
        "selected_ear_symptoms","neck_shoulder_symptoms","additional_symptoms","neck_trauma_radio",
        "stress_radio","stress_detail","ortho_exp","ortho_detail","prosth_exp","prosth_detail",
        "other_dental","tmd_treatment_history","tmd_treatment_detail","tmd_treatment_response",
        "tmd_current_medications","past_history","current_medications","bite_right","bite_left",
        "loading_test","resistance_test","attrition","impact_daily","impact_work","impact_quality_of_life",
        "sleep_quality","sleep_tmd_relation","diagnosis_result"
    ]

    import textwrap
    values = {k: str(st.session_state.get(k, "")) for k in keys}
    values = {k: ("" if v == "선택 안 함" else v) for k, v in values.items()}

    for long_key in ["additional_habits", "past_history", "current_medications"]:
        if long_key in values:
            values[long_key] = "\n".join(textwrap.wrap(values[long_key], width=70))
    
    for page in doc:
        placeholders_to_insert = {}
        for key, val in values.items():
            placeholder = f"{{{key}}}"
            rects = page.search_for(placeholder)
            if rects:
                placeholders_to_insert[key] = {'value': val, 'rects': rects}
                for rect in rects:
                    page.add_redact_annot(rect)

        page.apply_redactions()

        for key, data in placeholders_to_insert.items():
            val = data['value']
            rects = data['rects']
            for rect in rects:
                x, y = rect.tl
                for i, line in enumerate(val.split("\n")):
                    page.insert_text((x, y + 8 + i*12), line, fontname="nan", fontfile=FONT_FILE, fontsize=10)

    # ✅ (시작) --- 업로드된 이미지를 PDF에 추가하는 새 코드 ---
    uploaded_images = st.session_state.get("uploaded_images", [])
    if uploaded_images:
        for i, uploaded_image in enumerate(uploaded_images):
            # 새 페이지를 A4 사이즈로 추가
            page = doc.new_page(width=fitz.paper_size("a4")[0], height=fitz.paper_size("a4")[1])
            
            # 페이지 상단에 제목 추가
            title_rect = fitz.Rect(50, 50, page.rect.width - 50, 80)
            page.insert_textbox(title_rect, f"첨부된 증빙 자료 {i+1}", fontsize=14, fontname="nan", fontfile=FONT_FILE, align=fitz.TEXT_ALIGN_CENTER)

            # 이미지 데이터를 바이트로 읽기
            img_bytes = uploaded_image.getvalue()

            # 이미지를 삽입할 영역 계산 (여백 고려)
            margin = 50
            image_area = fitz.Rect(margin, 100, page.rect.width - margin, page.rect.height - margin)
            
            # 페이지에 이미지 삽입 (가로/세로 비율 유지하며 영역에 맞게)
            page.insert_image(image_area, stream=img_bytes, keep_proportion=True)
    # ✅ (끝) --- 이미지 추가 코드 ---

    pdf_buffer = BytesIO()
    doc.save(pdf_buffer)
    doc.close()
    pdf_buffer.seek(0)
    return pdf_buffer


# --- 페이지 설정 ---
st.set_page_config(
    page_title="턱관절 자가 문진 시스템 | 스마트 헬스케어",
    layout="wide", 
    initial_sidebar_state="collapsed",
    menu_items={
        'About': '이 앱은 턱관절 자가 문진을 위한 도구입니다.'
    }
)# --- 헬퍼 함수 ---
def go_next():
    st.session_state.step += 1
    st.session_state.validation_errors = {} # 다음 단계로 넘어갈 때 에러 초기화
def go_back():
    st.session_state.step -= 1
    st.session_state.validation_errors = {} # 이전 단계로 돌아갈 때 에러 초기화
# 진단 함수
def compute_diagnoses(state):
    diagnoses = []

    def is_yes(val): return val == "예"
    def is_no(val): return val == "아니오"

    # 1. 국소 근육통 (Local Myalgia)
    if (
        is_yes(state.get("muscle_pressure_2s_value")) and
        is_yes(state.get("muscle_referred_pain_value")) and
        is_no(state.get("muscle_referred_remote_pain_value"))
    ):
        diagnoses.append("국소 근육통 (Local Myalgia)")

    # 2. 방사성 근막통 (Myofascial Pain with Referral)
    if (
        is_yes(state.get("muscle_pressure_2s_value")) and
        is_yes(state.get("muscle_referred_pain_value")) and
        is_yes(state.get("muscle_referred_remote_pain_value"))
    ):
        diagnoses.append("방사성 근막통 (Myofascial Pain with Referral)")

    # 3. 근육통 (Myalgia) — 국소/방사성이 없을 때만
    if (
        "국소 근육통 (Local Myalgia)" not in diagnoses and
        "방사성 근막통 (Myofascial Pain with Referral)" not in diagnoses
    ):
        if is_no(state.get("muscle_pressure_2s_value")):
            diagnoses.append("근육통 (Myalgia)")
        elif is_yes(state.get("muscle_pressure_2s_value")) and is_no(state.get("muscle_referred_pain_value")):
            diagnoses.append("근육통 (Myalgia)")

    # 4. 관절통 (Arthralgia)
    if is_yes(state.get("tmj_press_pain_value")):
        diagnoses.append("관절통 (Arthralgia)")

    # 5. TMD에 기인한 두통
    if (
        state.get("headache_with_jaw_value") == "예" and
        all(is_yes(state.get(k)) for k in [
            "headache_temples_value",
            "headache_reproduce_by_pressure_value",
            "headache_not_elsewhere_value",
            "headache_with_jaw_value"
        ])
    ) or (
        state.get("headache_with_jaw_value") == "아니오" and
        is_yes(state.get("headache_temples_value")) and
        is_yes(state.get("headache_reproduce_by_pressure_value"))
    ):
        diagnoses.append("TMD에 기인한 두통 (Headache attributed to TMD)")

    # 6. 퇴행성 관절 질환
    if is_yes(state.get("crepitus_confirmed_value")):
        diagnoses.append("퇴행성 관절 질환 (Degenerative Joint Disease)")

    # 7. 비정복성 관절원판 변위, 개구 제한 없음
    if is_yes(state.get("mao_fits_3fingers_value")):
        diagnoses.append("비정복성 관절원판 변위, 개구 제한 없음 (Disc Displacement without Reduction)")

    # 8. 비정복성 관절원판 변위, 개구 제한 동반
    if (
        is_no(state.get("mao_fits_3fingers_value")) or
        is_no(state.get("jaw_unlock_possible_value"))
    ):
        diagnoses.append("비정복성 관절원판 변위, 개구 제한 동반 (Disc Displacement without Reduction with Limited opening)")

    # 9. 정복성 관절원판 변위, 간헐적 개구 장애 동반
    if (
        is_yes(state.get("jaw_locked_now_value")) and
        is_yes(state.get("jaw_unlock_possible_value"))
    ):
        diagnoses.append("정복성 관절원판 변위, 간헐적 개구 장애 동반 (Disc Displacement with reduction, with intermittent locking)")

    # 10. 정복성 관절원판 변위 (딸깍 소리 있을 경우)
    if state.get("tmj_sound_value") and "딸깍" in state.get("tmj_sound_value"):
        diagnoses.append("정복성 관절원판 변위 (Disc Displacement with Reduction)")

    return diagnoses



# 콜백 함수 정의
# Place this function at the top of your script
def sync_widget_key(widget_key, target_key):
    if widget_key in st.session_state:
        st.session_state[target_key] = st.session_state[widget_key]


def update_headache_frequency():
    st.session_state["headache_frequency"] = st.session_state["headache_frequency_widget"]
    
def update_radio_state(key):
    st.session_state[key] = st.session_state.get(key)

def update_text_state(key):
    st.session_state[key] = st.session_state.get(key, "")
    
# ✅ (유지) 여러 개 복사
def sync_multiple_keys(field_mapping):
    for widget_key, session_key in field_mapping.items():
        st.session_state[session_key] = st.session_state.get(widget_key, "")

# ✅ (유지) 일반적인 widget → session 복사
def sync_widget_key(widget_key, target_key):
    if widget_key in st.session_state:
        st.session_state[target_key] = st.session_state[widget_key]

# ✅ (유지) '목/어깨 증상' 전용 로직
def update_neck_none():
    if st.session_state.get('neck_none'):
        st.session_state['neck_pain'] = False
        st.session_state['shoulder_pain'] = False
        st.session_state['stiffness'] = False

def update_neck_symptom(key):
    if st.session_state.get(key):
        st.session_state['neck_none'] = False
        
def sync_widget_to_session(widget_key, session_key):
    """
    Streamlit 위젯의 현재 값을 세션 상태에 동기화하는 콜백 함수
    """
    if widget_key in st.session_state:
        st.session_state[session_key] = st.session_state[widget_key]


def update_radio_state(key):
    st.session_state[key] = st.session_state.get(key)

def update_text_state(key):
    st.session_state[key] = st.session_state.get(key, "")

def reset_headache_details():
    if st.session_state.get("has_headache_widget") != "예":
        # 두통이 '예'가 아니면 모든 관련 키들을 초기화
        keys_to_reset = [
            "headache_areas",
            "headache_severity",
            "headache_frequency",
            "headache_triggers",
            "headache_reliefs"
        ]
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]

def restart_app():
    # 세션 상태 전체 삭제
    st.session_state.clear()

    # 필수 키 다시 초기화
    st.session_state.step = 0
    st.session_state.reset_confirm = False
    # 필요 시 다른 기본 키들도 여기서 재설정
    # st.session_state.setdefault("neck_shoulder_symptoms", DEFAULT_SYMPTOMS.copy())

    # 앱을 맨 위에서 다시 실행
    st.rerun()

# ---------------------------------------------

# 총 단계 수 (0부터 시작)
total_steps = 20 
# --- 사이드바 ---
st.sidebar.button(
    "🔄 처음부터 다시 시작",
    key="btn_request_reset",
    on_click=restart_app
)
# 사이드바: 저장·불러오기 버튼
if st.sidebar.button("📥 저장하기", on_click=save_session):
    pass

if st.sidebar.button("📂 불러오기", on_click=load_session):
    pass

if st.sidebar.button("🗑️ 세션 삭제", on_click=delete_session):
    pass
st.sidebar.markdown("# 시스템 정보")
st.sidebar.info("이 시스템은 턱관절 건강 자가 점검을 돕기 위해 개발되었습니다. 제공되는 정보는 참고용이며, 의료 진단을 대체할 수 없습니다.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**현재 단계: {st.session_state.step + 1}/{total_steps + 1}**")
st.sidebar.progress((st.session_state.step + 1) / (total_steps + 1))
st.sidebar.markdown("---")
st.sidebar.markdown("### ❓ FAQ")
with st.sidebar.expander("턱관절 질환이란?"):
    st.write("턱관절 질환은 턱 주변의 근육, 관절, 인대 등에 문제가 생겨 통증, 소리, 개구 제한 등을 유발하는 상태를 말합니다.")
with st.sidebar.expander("자가 문진의 의미는?"):
    st.write("간단한 문진을 통해 스스로 증상을 파악하고, 전문가 진료의 필요성을 가늠해 볼 수 있는 초기 단계의 검사입니다.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📞 문의")
st.sidebar.write("contact@example.com") # 실제 이메일 주소로 변경
st.sidebar.write("000-1234-5678") # 실제 전화번호로 변경
# --- 메인 UI 렌더링 ---
st.title("🦷 턱관절 자가 문진 시스템")
st.markdown("---")
# STEP 0: Welcome Page (새로 추가된 단계)
if st.session_state.step == 0:
    st.header("✨ 당신의 턱관절 건강, 지금 바로 확인하세요!")
    st.write("""
    이 시스템은 턱관절 건강 상태를 스스로 점검하고, 잠재적인 문제를 조기에 파악할 수 있도록 설계되었습니다.
    간단한 몇 단계의 설문을 통해, 맞춤형 예비 진단 결과를 받아보세요.
    """)
    
    st.markdown("---")
    
    col_intro1, col_intro2, col_intro3 = st.columns(3)
    with col_intro1:
        st.info("**🚀 신속한 검사:** 짧은 시간 안에 주요 증상 확인")
    with col_intro2:
        st.info("**📊 직관적인 결과:** 시각적으로 이해하기 쉬운 진단 요약")
    with col_intro3:
        st.info("**📝 보고서 생성:** 개인 맞춤형 PDF 보고서 제공")
    st.markdown("---")
    with st.expander("시작하기 전에 꼭 읽어주세요!"):
        st.markdown("""
        * 본 시스템은 **의료 진단을 대체하지 않습니다.** 정확한 진단과 치료는 반드시 전문 의료기관을 방문하시기 바랍니다.
        * 제공된 모든 정보는 **익명으로 처리**되며, 개인 정보 보호를 최우선으로 합니다.
        * 솔직하게 답변해주시면 더욱 정확한 예비 진단 결과를 얻을 수 있습니다.
        """)

    if 'show_exercise' not in st.session_state:
       st.session_state.show_exercise = False

    if not st.session_state.show_exercise:
        # 버튼 key 이름을 'btn_show_exercise' 같이 다르게 설정
        if st.button("턱관절 운동 안내 보기", key="btn_show_exercise"):
            st.session_state.show_exercise = True
    else:
        exercise_img_path = "tmj_exercise.png"
        if os.path.exists(exercise_img_path):
            st.image(exercise_img_path, use_container_width=True)
        else:
            st.warning(f"운동 안내 이미지({exercise_img_path})를 찾을 수 없습니다.")

        # 닫기 버튼도 key 이름 변경
        if st.button("운동 안내 닫기", key="btn_hide_exercise"):
            st.session_state.show_exercise = False

    
    st.markdown("---")
    if st.button("문진 시작하기 🚀", use_container_width=True):
        go_next() # Step 1로 이동 (기존 코드의 Step 0)
        st.session_state.step = 1
# 세션 상태가 업데이트된 후, 스크립트를 즉시 다시 실행
        st.rerun()


# STEP 1: 환자 정보 입력
elif st.session_state.step == 1:
    st.header("📝 환자 기본 정보 입력")
    st.write("정확한 문진을 위해 필수 정보를 입력해주세요. (*표시는 필수 항목입니다.)")

    # 매핑 정의: widget_key → state_key
    field_mapping = {
        "name_widget": "name",
        "birthdate_widget": "birthdate",
        "gender_widget": "gender",
        "email_widget": "email",
        "phone_widget": "phone",
        "address_widget": "address",
        "occupation_widget": "occupation",
        "visit_reason_widget": "visit_reason",
    }

    with st.container(border=True):
        col_name, col_birthdate = st.columns(2)
        with col_name:
            st.text_input("이름*", key="name_widget", value=st.session_state.get("name", ""),
                          placeholder="이름을 입력하세요",
                          on_change=sync_widget_key, args=("name_widget", "name"))
            if 'name' in st.session_state.get("validation_errors", {}):
                st.error(st.session_state.validation_errors['name'])

        with col_birthdate:
            st.date_input("생년월일*", key="birthdate_widget",
                          value=st.session_state.get("birthdate", datetime.date(2000, 1, 1)),
                          min_value=datetime.date(1900, 1, 1),
                          on_change=sync_widget_key, args=("birthdate_widget", "birthdate"))

        st.radio("성별*", ["남성", "여성", "기타", "선택 안 함"],
                 key="gender_widget",
                 index=["남성", "여성", "기타", "선택 안 함"].index(st.session_state.get("gender", "선택 안 함")),
                 horizontal=True,
                 on_change=sync_widget_key, args=("gender_widget", "gender"))
        if 'gender' in st.session_state.get("validation_errors", {}):
            st.error(st.session_state.validation_errors['gender'])

        col_email, col_phone = st.columns(2)
        with col_email:
            st.text_input("이메일*", key="email_widget", value=st.session_state.get("email", ""),
                          placeholder="예: user@example.com",
                          on_change=sync_widget_key, args=("email_widget", "email"))
            if 'email' in st.session_state.get("validation_errors", {}):
                st.error(st.session_state.validation_errors['email'])

        with col_phone:
            st.text_input("연락처*", key="phone_widget",
                          value=st.session_state.get("phone", ""),
                          placeholder="예: 01012345678 (숫자만 입력)",
                          on_change=sync_widget_key, args=("phone_widget", "phone"))
            if 'phone' in st.session_state.get("validation_errors", {}):
                st.error(st.session_state.validation_errors['phone'])

        st.markdown("---")
        st.text_input("주소 (선택 사항)", key="address_widget", value=st.session_state.get("address", ""),
                      placeholder="도로명 주소 또는 지번 주소",
                      on_change=sync_widget_key, args=("address_widget", "address"))
        st.text_input("직업 (선택 사항)", key="occupation_widget", value=st.session_state.get("occupation", ""),
                      placeholder="직업을 입력하세요",
                      on_change=sync_widget_key, args=("occupation_widget", "occupation"))
        st.text_area("내원 목적 (선택 사항)", key="visit_reason_widget", value=st.session_state.get("visit_reason", ""),
                     placeholder="예: 턱에서 소리가 나고 통증이 있어서 진료를 받고 싶습니다.",
                     on_change=sync_widget_key, args=("visit_reason_widget", "visit_reason"))

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 0
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            # 강제 복사: 혹시라도 on_change가 실행되지 않은 위젯 처리
            sync_multiple_keys(field_mapping)

            # 유효성 검사
            st.session_state.validation_errors = {}
            mandatory_fields_filled = True

            if not st.session_state.get('name'):
                st.session_state.validation_errors['name'] = "이름은 필수 입력 항목입니다."
                mandatory_fields_filled = False
            if st.session_state.get('gender') == '선택 안 함':
                st.session_state.validation_errors['gender'] = "성별은 필수 선택 항목입니다."
                mandatory_fields_filled = False
            if not st.session_state.get('email'):
                st.session_state.validation_errors['email'] = "이메일은 필수 입력 항목입니다."
                mandatory_fields_filled = False
            if not st.session_state.get('phone'):
                st.session_state.validation_errors['phone'] = "연락처는 필수 입력 항목입니다."
                mandatory_fields_filled = False

            if mandatory_fields_filled:
                st.session_state.step = 2
            st.rerun()


# STEP 2: 주호소 - 수정된 코드

elif st.session_state.step == 2:
    st.title("주 호소 (Chief Complaint)")
    st.markdown("---")

    # 매핑 정의: widget_key → state_key
    field_mapping = {
        "chief_complaint_widget": "chief_complaint",
        "chief_complaint_other_widget": "chief_complaint_other",
        "onset_widget": "onset"
    }

    with st.container(border=True):
        st.markdown("**이번에 병원을 방문한 주된 이유는 무엇인가요?**")
        
        # 1. 옵션 리스트를 변수로 정의합니다.
        complaint_options = [
            "턱 주변의 통증(턱 근육, 관자놀이, 귀 앞쪽)",
            "턱관절 소리/잠김",
            "턱 움직임 관련 두통",
            "기타 불편한 증상",
            "선택 안 함"
        ]
        
        st.radio(
            label="",
            options=complaint_options,
            key="chief_complaint_widget",
            # 2. session_state에 저장된 값을 기반으로 index를 동적으로 설정합니다.
            index=complaint_options.index(st.session_state.get("chief_complaint", "선택 안 함")),
            label_visibility="collapsed",
            on_change=sync_widget_key,
            args=("chief_complaint_widget", "chief_complaint")
        )

        if st.session_state.get("chief_complaint") == "기타 불편한 증상":
            st.text_input(
                "기타 사유를 적어주세요:",
                key="chief_complaint_other_widget",
                value=st.session_state.get("chief_complaint_other", ""),
                on_change=sync_widget_key,
                args=("chief_complaint_other_widget", "chief_complaint_other")
            )
        # '기타'가 아닐 때 값을 비우는 로직은 그대로 유지하는 것이 좋습니다.
        elif "chief_complaint_other" in st.session_state:
             st.session_state["chief_complaint_other"] = ""


        st.markdown("---")
        st.markdown("**문제가 처음 발생한 시기가 어떻게 되나요?**")
        onset_options = [
            "일주일 이내", "1개월 이내", "6개월 이내", "1년 이내", "1년 이상 전", "선택 안 함"
        ]
        st.radio(
            label="",
            options=onset_options,
            index=onset_options.index(st.session_state.get("onset", "선택 안 함")),
            key="onset_widget",
            label_visibility="collapsed",
            on_change=sync_widget_key,
            args=("onset_widget", "onset")
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 1
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            sync_multiple_keys(field_mapping)

            complaint = st.session_state.get("chief_complaint")
            other_text = st.session_state.get("chief_complaint_other", "").strip()
            onset_selected = st.session_state.get("onset")

            if complaint == "선택 안 함":
                st.warning("주 호소 항목을 선택해주세요.")
            elif complaint == "기타 불편한 증상" and not other_text:
                st.warning("기타 증상을 입력해주세요.")
            elif onset_selected == "선택 안 함":
                st.warning("문제 발생 시기를 선택해주세요.")
            else:
                # 다음 단계로 넘어가는 로직은 기존과 동일합니다.
                if complaint in ["턱 주변의 통증(턱 근육, 관자놀이, 귀 앞쪽)", "턱 움직임 관련 두통"]:
                    st.session_state.step = 3
                elif complaint == "턱관절 소리/잠김":
                    st.session_state.step = 5
                elif complaint == "기타 불편한 증상":
                    st.session_state.step = 6
                st.rerun()

# STEP 3: 통증 양상 - 수정된 코드

elif st.session_state.step == 3:
    st.title("현재 증상 (통증 양상)")
    st.markdown("---")

    # 위젯 → 저장용 키 매핑
    field_mapping = {
        "jaw_aggravation_widget": "jaw_aggravation",
        "pain_quality_widget": "pain_quality",
    }

    with st.container(border=True):
        st.markdown("**턱을 움직이거나 씹기, 말하기 등의 기능 또는 악습관(이갈이, 턱 괴기 등)으로 인해 통증이 악화되나요?**")
        
        # 옵션 리스트를 변수로 정의
        aggravation_options = ["예", "아니오", "선택 안 함"]
        
        st.radio(
            label="악화 여부",
            options=aggravation_options,
            key="jaw_aggravation_widget",
            # ✅ 해결: session_state 값에 따라 index를 동적으로 계산
            index=aggravation_options.index(st.session_state.get("jaw_aggravation", "선택 안 함")),
            label_visibility="collapsed",
            on_change=sync_widget_key,
            args=("jaw_aggravation_widget", "jaw_aggravation")
        )

        st.markdown("---")
        st.markdown("**통증을 어떻게 표현하시겠습니까? (예: 둔함, 날카로움, 욱신거림 등)**")
        
        # 옵션 리스트를 변수로 정의
        quality_options = ["둔함", "날카로움", "욱신거림", "간헐적", "선택 안 함"]

        st.radio(
            label="통증 양상",
            options=quality_options,
            key="pain_quality_widget",
            # ✅ 해결: session_state 값에 따라 index를 동적으로 계산
            index=quality_options.index(st.session_state.get("pain_quality", "선택 안 함")),
            label_visibility="collapsed",
            on_change=sync_widget_key,
            args=("pain_quality_widget", "pain_quality")
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    # 이전 단계
    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 2
            st.rerun()

    # 다음 단계
    with col2:
        if st.button("다음 단계로 이동 👉"):
            sync_multiple_keys(field_mapping)

            if st.session_state.get("jaw_aggravation", "선택 안 함") == "선택 안 함":
                st.warning("악화 여부는 필수 항목입니다. 선택해주세요.")
            elif st.session_state.get("pain_quality", "선택 안 함") == "선택 안 함":
                st.warning("통증 양상 항목을 선택해주세요.")
            else:
                st.session_state.step = 4
                st.rerun()
                
# STEP 4: 통증 부위 - 수정된 코드

elif st.session_state.step == 4:
    st.title("현재 증상 (통증 분류 및 검사)")
    st.markdown("---")

    pain_type_options = ["선택 안 함", "넓은 부위의 통증", "근육 통증", "턱관절 통증", "두통"]
    yes_no_options = ["예", "아니오", "선택 안 함"]

    # 세션 초기화 (기존과 동일)
    for key in [
        "pain_types_value", "muscle_movement_pain_value", "muscle_pressure_2s_value",
        "muscle_referred_pain_value", "muscle_referred_remote_pain_value",
        "tmj_movement_pain_value", "tmj_press_pain_value",
        "headache_temples_value", "headache_with_jaw_value",
        "headache_reproduce_by_pressure_value", "headache_not_elsewhere_value"
    ]:
        st.session_state.setdefault(key, "선택 안 함")

    def get_radio_index(key, options=yes_no_options):
        # get() 메서드의 기본값으로 "선택 안 함"을 사용하여 안전하게 처리
        val = st.session_state.get(key, "선택 안 함")
        return options.index(val) if val in options else len(options) - 1

    def update_session(key, widget_key):
        st.session_state[key] = st.session_state.get(widget_key)

    # UI (기존과 거의 동일)
    with st.container(border=True):
        st.markdown("**아래 중 해당되는 통증 유형을 선택해주세요.**")
        st.selectbox("",
            pain_type_options,
            index=pain_type_options.index(st.session_state.get("pain_types_value", "선택 안 함")),
            key="pain_types_widget_key",
            on_change=update_session,
            args=("pain_types_value", "pain_types_widget_key")
        )

        st.markdown("---")
        pain_type = st.session_state.get("pain_types_value")

        # 이하의 모든 st.radio 및 st.selectbox 코드는 기존과 동일하게 유지합니다.
        # ... (생략된 기존 위젯 코드) ...
        if pain_type in ["넓은 부위의 통증", "근육 통증"]:
            st.markdown("#### 💬 근육/넓은 부위 관련")
            st.markdown("**입을 벌릴 때나 턱을 움직일 때 통증이 있나요?**")
            st.radio("", yes_no_options, index=get_radio_index("muscle_movement_pain_value"),
                     key="muscle_movement_pain_widget_key",
                     on_change=update_session, args=("muscle_movement_pain_value", "muscle_movement_pain_widget_key"))

            st.markdown("**근육을 2초간 눌렀을 때 통증이 느껴지나요?**")
            st.radio("", yes_no_options, index=get_radio_index("muscle_pressure_2s_value"),
                     key="muscle_pressure_2s_widget_key",
                     on_change=update_session, args=("muscle_pressure_2s_value", "muscle_pressure_2s_widget_key"))

            if st.session_state.get("muscle_pressure_2s_value") == "예":
                st.markdown("**근육을 5초간 눌렀을 때, 통증이 눌린 부위 넘어서 퍼지나요?**")
                st.radio("", yes_no_options, index=get_radio_index("muscle_referred_pain_value"),
                         key="muscle_referred_pain_widget_key",
                         on_change=update_session, args=("muscle_referred_pain_value", "muscle_referred_pain_widget_key"))

                if st.session_state.get("muscle_referred_pain_value") == "예":
                    st.markdown("**통증이 눌린 부위 외 다른 곳(눈, 귀 등)까지 퍼지나요?**")
                    st.radio("", yes_no_options, index=get_radio_index("muscle_referred_remote_pain_value"),
                             key="muscle_referred_remote_pain_widget_key",
                             on_change=update_session, args=("muscle_referred_remote_pain_value", "muscle_referred_remote_pain_widget_key"))

        elif pain_type == "턱관절 통증":
            st.markdown("#### 💬 턱관절 관련")
            st.markdown("**입을 벌릴 때나 움직일 때 통증이 있나요?**")
            st.radio("", yes_no_options, index=get_radio_index("tmj_movement_pain_value"),
                     key="tmj_movement_pain_widget_key",
                     on_change=update_session, args=("tmj_movement_pain_value", "tmj_movement_pain_widget_key"))

            st.markdown("**턱관절 부위를 눌렀을 때 기존 통증이 재현되나요?**")
            st.radio("", yes_no_options, index=get_radio_index("tmj_press_pain_value"),
                     key="tmj_press_pain_widget_key",
                     on_change=update_session, args=("tmj_press_pain_value", "tmj_press_pain_widget_key"))

        elif pain_type == "두통":
            st.markdown("#### 💬 두통 관련")
            st.markdown("**두통이 관자놀이 부위에서 발생하나요?**")
            st.radio("", yes_no_options, index=get_radio_index("headache_temples_value"),
                     key="headache_temples_widget_key",
                     on_change=update_session, args=("headache_temples_value", "headache_temples_widget_key"))

            st.markdown("**관자놀이 근육을 눌렀을 때 기존 두통이 재현되나요?**")
            st.radio("", yes_no_options, index=get_radio_index("headache_reproduce_by_pressure_value"),
                     key="headache_reproduce_by_pressure_widget_key",
                     on_change=update_session, args=("headache_reproduce_by_pressure_value", "headache_reproduce_by_pressure_widget_key"))

            st.markdown("**턱을 움직일 때 두통이 심해지나요?**")
            st.radio("", yes_no_options, index=get_radio_index("headache_with_jaw_value"),
                     key="headache_with_jaw_widget_key",
                     on_change=update_session, args=("headache_with_jaw_value", "headache_with_jaw_widget_key"))

            if st.session_state.get("headache_with_jaw_value") == "예":
                st.markdown("**해당 두통이 다른 의학적 진단으로 설명되지 않나요?**")
                st.radio("", yes_no_options, index=get_radio_index("headache_not_elsewhere_value"),
                         key="headache_not_elsewhere_widget_key",
                         on_change=update_session, args=("headache_not_elsewhere_value", "headache_not_elsewhere_widget_key"))

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            # ✅ 해결: 데이터 삭제 로직을 완전히 제거합니다.
            st.session_state.step = 3
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            errors = []
            pain_type = st.session_state.get("pain_types_value")
            if pain_type == "선택 안 함":
                errors.append("통증 유형을 선택해주세요.")

            # ... (기존 유효성 검사 로직은 그대로 유지) ...
            if pain_type in ["넓은 부위의 통증", "근육 통증"]:
                if st.session_state.get("muscle_movement_pain_value") == "선택 안 함": errors.append("근육: 입 벌릴 때 통증 여부를 선택해주세요.")
                if st.session_state.get("muscle_pressure_2s_value") == "선택 안 함": errors.append("근육: 2초간 압통 여부를 선택해주세요.")
                if st.session_state.get("muscle_pressure_2s_value") == "예":
                    if st.session_state.get("muscle_referred_pain_value") == "선택 안 함": errors.append("근육: 5초간 통증 전이 여부를 선택해주세요.")
                    elif st.session_state.get("muscle_referred_pain_value") == "예" and st.session_state.get("muscle_referred_remote_pain_value") == "선택 안 함": errors.append("근육: 통증이 다른 부위까지 퍼지는지 여부를 선택해주세요.")
            if pain_type == "턱관절 통증":
                if st.session_state.get("tmj_movement_pain_value") == "선택 안 함": errors.append("턱관절: 움직일 때 통증 여부를 선택해주세요.")
                if st.session_state.get("tmj_press_pain_value") == "선택 안 함": errors.append("턱관절: 눌렀을 때 통증 여부를 선택해주세요.")
            if pain_type == "두통":
                if st.session_state.get("headache_temples_value") == "선택 안 함": errors.append("두통: 관자놀이 여부를 선택해주세요.")
                if st.session_state.get("headache_reproduce_by_pressure_value") == "선택 안 함": errors.append("두통: 관자놀이 압통 시 두통 재현 여부를 선택해주세요.")
                if st.session_state.get("headache_with_jaw_value") == "선택 안 함": errors.append("두통: 턱 움직임 시 두통 악화 여부를 선택해주세요.")
                if st.session_state.get("headache_with_jaw_value") == "예" and st.session_state.get("headache_not_elsewhere_value") == "선택 안 함": errors.append("두통: 다른 진단 여부를 선택해주세요.")

            if errors:
                for err in errors:
                    st.warning(err)
            else:
                st.session_state.step = 6
                st.rerun()

# STEP 5: 턱관절 소리 및 잠김
elif st.session_state.step == 5:
    st.title("현재 증상 (턱관절 소리 및 잠김 증상)")
    st.markdown("---")

    st.session_state.setdefault("tmj_sound_value", "선택 안 함")
    st.session_state.setdefault("crepitus_confirmed_value", "선택 안 함")
    st.session_state.setdefault("tmj_click_context", [])
    st.session_state.setdefault("jaw_locked_now_value", "선택 안 함")
    st.session_state.setdefault("jaw_unlock_possible_value", "선택 안 함")
    st.session_state.setdefault("jaw_locked_past_value", "선택 안 함")
    st.session_state.setdefault("mao_fits_3fingers_value", "선택 안 함")

    def get_radio_index(key_value, options):
        val = st.session_state.get(key_value, "선택 안 함")
        return options.index(val) if val in options else options.index("선택 안 함")

    def update_tmj_sound():
        st.session_state.tmj_sound_value = st.session_state.tmj_sound_widget_key

    def update_crepitus_confirmed():
        st.session_state.crepitus_confirmed_value = st.session_state.crepitus_confirmed_widget_key

    def update_jaw_locked_now():
        st.session_state.jaw_locked_now_value = st.session_state.jaw_locked_now_widget_key

    def update_jaw_unlock_possible():
        st.session_state.jaw_unlock_possible_value = st.session_state.jaw_unlock_possible_widget_key

    def update_jaw_locked_past():
        st.session_state.jaw_locked_past_value = st.session_state.jaw_locked_past_widget_key

    def update_mao_fits_3fingers():
        st.session_state.mao_fits_3fingers_value = st.session_state.mao_fits_3fingers_widget_key

    joint_sound_options = ["딸깍소리", "사각사각소리(크레피투스)", "없음", "선택 안 함"]
    st.markdown("**턱에서 나는 소리가 있나요?**")
    st.radio(
        "턱에서 나는 소리를 선택하세요.",
        options=joint_sound_options,
        key="tmj_sound_widget_key",
        index=get_radio_index("tmj_sound_value", joint_sound_options),
        on_change=update_tmj_sound
    )

    if st.session_state.tmj_sound_value == "딸깍소리":
        st.markdown("**딸깍 소리가 나는 상황을 모두 선택하세요.**")
        click_options = ["입 벌릴 때", "입 다물 때", "음식 씹을 때"]
        updated_context = []
        for option in click_options:
            key = f"click_{option}"
            is_checked = option in st.session_state.tmj_click_context
            if st.checkbox(f"- {option}", value=is_checked, key=key):
                updated_context.append(option)
        st.session_state.tmj_click_context = updated_context

    elif st.session_state.tmj_sound_value == "사각사각소리(크레피투스)":
        crepitus_options = ["예", "아니오", "선택 안 함"]
        st.radio(
            "**사각사각소리가 확실하게 느껴지나요?**",
            options=crepitus_options,
            key="crepitus_confirmed_widget_key",
            index=get_radio_index("crepitus_confirmed_value", crepitus_options),
            on_change=update_crepitus_confirmed
        )

    show_lock_questions = (
        st.session_state.tmj_sound_value == "사각사각소리(크레피투스)" and
        st.session_state.crepitus_confirmed_value == "아니오"
    )

    if show_lock_questions:
        st.markdown("---")
        st.radio(
            "**현재 턱이 걸려서 입이 잘 안 벌어지는 증상이 있나요?**",
            options=["예", "아니오", "선택 안 함"],
            key="jaw_locked_now_widget_key",
            index=get_radio_index("jaw_locked_now_value", ["예", "아니오", "선택 안 함"]),
            on_change=update_jaw_locked_now
        )

        if st.session_state.jaw_locked_now_value == "예":
            st.radio(
                "**해당 증상은 조작해야 풀리나요?**",
                options=["예", "아니오", "선택 안 함"],
                key="jaw_unlock_possible_widget_key",
                index=get_radio_index("jaw_unlock_possible_value", ["예", "아니오", "선택 안 함"]),
                on_change=update_jaw_unlock_possible
            )
        elif st.session_state.jaw_locked_now_value == "아니오":
            st.radio(
                "**과거에 턱 잠김 또는 개방성 잠김을 경험한 적이 있나요?**",
                options=["예", "아니오", "선택 안 함"],
                key="jaw_locked_past_widget_key",
                index=get_radio_index("jaw_locked_past_value", ["예", "아니오", "선택 안 함"]),
                on_change=update_jaw_locked_past
            )
            if st.session_state.jaw_locked_past_value == "예":
                st.radio(
                    "**입을 최대한 벌렸을 때 (MAO), 손가락 3개가 들어가나요?**",
                    options=["예", "아니오", "선택 안 함"],
                    key="mao_fits_3fingers_widget_key",
                    index=get_radio_index("mao_fits_3fingers_value", ["예", "아니오", "선택 안 함"]),
                    on_change=update_mao_fits_3fingers
                )
            else:
                st.session_state.mao_fits_3fingers_value = "선택 안 함"
        else:
            st.session_state.jaw_unlock_possible_value = "선택 안 함"
            st.session_state.jaw_locked_past_value = "선택 안 함"
            st.session_state.mao_fits_3fingers_value = "선택 안 함"
    else:
        st.session_state.jaw_locked_now_value = "선택 안 함"
        st.session_state.jaw_unlock_possible_value = "선택 안 함"
        st.session_state.jaw_locked_past_value = "선택 안 함"
        st.session_state.mao_fits_3fingers_value = "선택 안 함"

    if st.session_state.tmj_sound_value != "딸깍소리":
        st.session_state.tmj_click_context = []

    # 딸깍소리 문맥 요약 정리 (PDF용)
    st.session_state.tmj_click_summary = (
        ", ".join(st.session_state.tmj_click_context)
        if st.session_state.tmj_click_context else "해당 없음"
    )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            for key in [
                "tmj_sound_value", "crepitus_confirmed_value", "tmj_click_context",
                "jaw_locked_now_value", "jaw_unlock_possible_value",
                "jaw_locked_past_value", "mao_fits_3fingers_value"
            ]:
                st.session_state.pop(key, None)
            st.session_state.step = 4
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            errors = []
            if st.session_state.tmj_sound_value == "선택 안 함":
                errors.append("턱관절 소리 여부를 선택해주세요.")
            if st.session_state.tmj_sound_value == "딸깍소리" and not st.session_state.tmj_click_context:
                errors.append("딸깍소리가 언제 나는지 최소 1개 이상 선택해주세요.")
            if st.session_state.tmj_sound_value == "사각사각소리(크레피투스)" and st.session_state.crepitus_confirmed_value == "선택 안 함":
                errors.append("사각사각소리가 확실한지 여부를 선택해주세요.")
            if show_lock_questions:
                if st.session_state.jaw_locked_now_value == "선택 안 함":
                    errors.append("현재 턱 잠김 여부를 선택해주세요.")
                if st.session_state.jaw_locked_now_value == "예" and st.session_state.jaw_unlock_possible_value == "선택 안 함":
                    errors.append("현재 턱 잠김이 조작으로 풀리는지 여부를 선택해주세요.")
                if st.session_state.jaw_locked_now_value == "아니오":
                    if st.session_state.jaw_locked_past_value == "선택 안 함":
                        errors.append("과거 턱 잠김 경험 여부를 선택해주세요.")
                    elif st.session_state.jaw_locked_past_value == "예" and st.session_state.mao_fits_3fingers_value == "선택 안 함":
                        errors.append("MAO 시 손가락 3개가 들어가는지 여부를 선택해주세요.")
            if errors:
                for err in errors:
                    st.warning(err)
            else:
                st.session_state.step = 6
                st.rerun()


# STEP 6: 빈도 및 시기, 강도 - 수정된 코드

elif st.session_state.step == 6:
    st.title("현재 증상 (빈도 및 시기)")
    st.markdown("---")

    # 위젯 키와 세션 상태 키 매핑
    widget_map = {
        "frequency_choice_widget": "frequency_choice",
        "pain_level_widget": "pain_level",
        "has_headache_widget": "has_headache_now",
        "headache_frequency_widget": "headache_frequency"
    }
    
    # 시간대 선택 옵션
    time_options = [
        {"key": "morning", "label": "오전"},
        {"key": "afternoon", "label": "오후"},
        {"key": "evening", "label": "저녁"},
    ]

    with st.container(border=True):
        st.markdown("**통증 또는 다른 증상이 얼마나 자주 발생하나요?**")
        freq_opts = ["주 1~2회", "주 3~4회", "주 5~6회", "매일", "선택 안 함"]
        st.radio(
            "",
            options=freq_opts,
            # ✅ 해결: session_state에 저장된 값을 기반으로 index를 동적으로 설정합니다.
            index=freq_opts.index(st.session_state.get("frequency_choice", "선택 안 함")),
            key="frequency_choice_widget",
            on_change=sync_widget_key,
            args=("frequency_choice_widget", "frequency_choice")
        )

        st.markdown("---")
        st.markdown("**(통증이 있을 시) 현재 통증 정도는 어느 정도인가요? (0=없음, 10=극심한 통증)**")
        st.slider(
            "통증 정도 선택", 0, 10,
            value=st.session_state.get("pain_level", 0),
            key="pain_level_widget",
            on_change=sync_widget_key,
            args=("pain_level_widget", "pain_level")
        )

        st.markdown("---")
        st.markdown("**주로 어느 시간대에 발생하나요?**")
        for time_opt in time_options:
            state_key = f"time_{time_opt['key']}"
            widget_key = f"{state_key}_widget"
            st.checkbox(
                label=time_opt['label'],
                value=st.session_state.get(state_key, False),
                key=widget_key,
                on_change=sync_widget_key,
                args=(widget_key, state_key)
            )

        st.markdown("---")
        st.markdown("**두통이 있나요?**")
        has_headache_options = ["예", "아니오", "선택 안 함"]
        st.radio(
            "", 
            options=has_headache_options,
            index=has_headache_options.index(st.session_state.get("has_headache_now", "선택 안 함")),
            key="has_headache_widget",
            on_change=handle_headache_change # on_change 콜백으로 로직 통합
        )

        # '예'를 선택했을 때만 두통 관련 질문 표시
        if st.session_state.get("has_headache_now") == "예":
            st.markdown("---")
            st.markdown("**두통 부위를 모두 선택해주세요.**")
            headache_area_opts = ["이마", "측두부(관자놀이)", "뒤통수", "정수리"]
            
            # 멀티셀렉트로 변경하여 상태 관리를 간소화
            selected_areas = st.multiselect(
                "두통 부위",
                options=headache_area_opts,
                default=st.session_state.get("headache_areas", []),
                key="headache_areas_widget"
            )
            st.session_state["headache_areas"] = selected_areas


            st.markdown("**현재 두통 강도는 얼마나 되나요? (0=없음, 10=극심한 통증)**")
            st.slider(
                "두통 강도", 0, 10, 
                value=st.session_state.get("headache_severity", 0),
                key="headache_severity_widget",
                on_change=sync_widget_key,
                args=("headache_severity_widget", "headache_severity")
            )


            st.markdown("**두통 빈도는 얼마나 자주 발생하나요?**")
            headache_freq_opts = ["주 1~2회", "주 3~4회", "주 5~6회", "매일", "선택 안 함"]
            st.radio(
                "", 
                options=headache_freq_opts,
                index=headache_freq_opts.index(st.session_state.get("headache_frequency", "선택 안 함")),
                key="headache_frequency_widget",
                on_change=sync_widget_key,
                args=("headache_frequency_widget", "headache_frequency")
            )
            
            st.markdown("**두통을 유발하거나 악화시키는 요인이 있나요? (복수 선택 가능)**")
            trigger_opts = ["스트레스", "수면 부족", "음식 섭취", "소음", "밝은 빛"]
            selected_triggers = st.multiselect(
                "유발/악화 요인",
                options=trigger_opts,
                default=st.session_state.get("headache_triggers", []),
                key="headache_triggers_widget"
            )
            st.session_state["headache_triggers"] = selected_triggers

            st.markdown("**두통을 완화시키는 요인이 있나요? (복수 선택 가능)**")
            relief_opts = ["휴식", "약물", "안마", "수면"]
            selected_reliefs = st.multiselect(
                "완화 요인",
                options=relief_opts,
                default=st.session_state.get("headache_reliefs", []),
                key="headache_reliefs_widget"
            )
            st.session_state["headache_reliefs"] = selected_reliefs

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계(주호소 질문으로)"):
            # 관련된 키들을 삭제하는 대신, 이전 단계로만 이동
            st.session_state.step = 2 
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            # 위젯 값들을 session_state로 최종 동기화
            sync_multiple_keys(widget_map)

            errors = []
            
            # 유효성 검사
            if st.session_state.get("frequency_choice", "선택 안 함") == "선택 안 함":
                errors.append("빈도 항목을 선택해주세요.")

            time_valid = any(st.session_state.get(f"time_{opt['key']}", False) for opt in time_options)
            if not time_valid:
                errors.append("시간대 항목을 하나 이상 선택해주세요.")

            if st.session_state.get("has_headache_now") == "예":
                if not st.session_state.get("headache_areas"):
                    errors.append("두통 부위를 최소 1개 이상 선택해주세요.")
                if st.session_state.get("headache_frequency") == "선택 안 함":
                    errors.append("두통 빈도를 선택해주세요.")
            
            if errors:
                for err in errors:
                    st.warning(err)
            else:
                # PDF 출력을 위해 선택된 시간대 텍스트로 저장
                selected_times_labels = [opt['label'] for opt in time_options if st.session_state.get(f"time_{opt['key']}")]
                st.session_state["selected_times"] = ", ".join(selected_times_labels) if selected_times_labels else "없음"
                
                st.session_state.step = 7
                st.rerun()

               
# STEP 7: 습관
elif st.session_state.step == 7:
    st.title("습관 (Habits)")
    st.markdown("---")

    with st.container(border=True):
        st.markdown("**다음 중 해당되는 습관이 있나요?**")

        first_habits = {
            "이갈이 - 밤(수면 중)": "habit_bruxism_night",
            "이 악물기 - 낮": "habit_clenching_day",
            "이 악물기 - 밤(수면 중)": "habit_clenching_night"
        }

        # 없음 체크박스
        st.checkbox(
            "없음",
            value=st.session_state.get("habit_none", False),
            key="habit_none_widget",
            on_change=sync_widget_key,
            args=("habit_none_widget", "habit_none")
        )

        none_checked = st.session_state.get("habit_none", False)

        for label, key in first_habits.items():
            widget_key = f"{key}_widget"
            st.checkbox(
                label,
                value=st.session_state.get(key, False),
                key=widget_key,
                on_change=sync_widget_key,
                args=(widget_key, key),
                disabled=none_checked
            )
            if not none_checked and key not in st.session_state:
                st.session_state[key] = False

        st.markdown("---")
        st.markdown("**다음 중 해당되는 습관이 있다면 모두 선택해주세요.**")

        additional_habits = [
            "옆으로 자는 습관", "코골이", "껌 씹기",
            "단단한 음식 선호(예: 견과류, 딱딱한 사탕 등)", "한쪽으로만 씹기",
            "혀 내밀기 및 밀기(이를 밀거나 입술 사이로 내미는 습관)", "손톱/입술/볼 물기",
            "손가락 빨기", "턱 괴기", "거북목/머리 앞으로 빼기",
            "음주", "흡연", "카페인"
        ]

        if "selected_habits" not in st.session_state:
            st.session_state.selected_habits = []

        for habit in additional_habits:
            widget_key = f"habit_{habit.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_').replace('.', '').replace(':', '')}_widget"

            checked = st.checkbox(
                habit,
                value=habit in st.session_state.selected_habits,
                key=widget_key
            )

            if checked and habit not in st.session_state.selected_habits:
                st.session_state.selected_habits.append(habit)
            elif not checked and habit in st.session_state.selected_habits:
                st.session_state.selected_habits.remove(habit)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 6
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            sync_multiple_keys({
                "habit_none_widget": "habit_none",
                "habit_bruxism_night_widget": "habit_bruxism_night",
                "habit_clenching_day_widget": "habit_clenching_day",
                "habit_clenching_night_widget": "habit_clenching_night",
            })

            # 습관 요약 생성
            first_habit_labels = {
                "habit_bruxism_night": "이갈이 (밤)",
                "habit_clenching_day": "이 악물기 (낮)",
                "habit_clenching_night": "이 악물기 (밤)",
            }

            first_selected = []

            if st.session_state.get("habit_none"):
                first_selected.append("없음")
            else:
                for key, label in first_habit_labels.items():
                    if st.session_state.get(key):
                        first_selected.append(label)

            habit_summary = ", ".join(first_selected) if first_selected else "없음"
            additional_summary = ", ".join(st.session_state.selected_habits) if st.session_state.selected_habits else "없음"

            st.session_state["habit_summary"] = habit_summary
            st.session_state["additional_habits"] = additional_summary
            st.session_state["full_habit_summary"] = f"주요 습관: {habit_summary}\n기타 습관: {additional_summary}"

            has_first = any([
                st.session_state.get("habit_bruxism_night", False),
                st.session_state.get("habit_clenching_day", False),
                st.session_state.get("habit_clenching_night", False),
                st.session_state.get("habit_none", False)
            ])

            if has_first:
                st.session_state.step = 8
                st.rerun()
            else:
                st.warning("‘이갈이/이 악물기/없음’ 중에서 최소 한 가지를 선택해주세요.")

# STEP 8: 턱 운동 범위 및 관찰1 (Range of Motion & Observations)
elif st.session_state.step == 8:
    st.title("턱 운동 범위 및 관찰 (Range of Motion & Observations)")
    st.markdown("---")
    st.markdown(
        "<span style='color:red;'>아래 항목은 실제 측정 및 검사가 필요할 수 있으며, 가능하신 부분만 기입해 주시면 됩니다. 나머지는 진료 중 확인할 수 있습니다.</span>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        # ⬛ 자발적 개구
        st.markdown("---")
        st.subheader("자발적 개구 (Active Opening)")

        st.markdown("**스스로 입을 크게 벌렸을 때 어느 정도까지 벌릴 수 있나요? (의료진이 측정 후 기록)**")
        st.text_input(
            label="",
            key="active_opening_widget",
            value=st.session_state.get("active_opening", ""),
            on_change=sync_widget_key,
            args=("active_opening_widget", "active_opening"),
            label_visibility="collapsed"
        )

        st.markdown("**통증이 있나요?**")
        st.radio(
            label="",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("active_pain", "선택 안 함")),
            key="active_pain_widget",
            on_change=sync_widget_key,
            args=("active_pain_widget", "active_pain"),
            label_visibility="collapsed"
        )

        # ⬛ 수동적 개구
        st.markdown("---")
        st.subheader("수동적 개구 (Passive Opening)")

        st.markdown("**타인이 도와서 벌렸을 때 어느 정도까지 벌릴 수 있나요? (의료진이 측정 후 기록)**")
        st.text_input(
            label="",
            key="passive_opening_widget",
            value=st.session_state.get("passive_opening", ""),
            on_change=sync_widget_key,
            args=("passive_opening_widget", "passive_opening"),
            label_visibility="collapsed"
        )

        st.markdown("**통증이 있나요?**")
        st.radio(
            label="",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("passive_pain", "선택 안 함")),
            key="passive_pain_widget",
            on_change=sync_widget_key,
            args=("passive_pain_widget", "passive_pain"),
            label_visibility="collapsed"
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 7
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            # 보완용 수동 복사
            sync_multiple_keys({
                "active_opening_widget": "active_opening",
                "active_pain_widget": "active_pain",
                "passive_opening_widget": "passive_opening",
                "passive_pain_widget": "passive_pain"
            })
            st.session_state.step = 9
            st.rerun()


# STEP 9: 턱 운동 범위 및 관찰2 (Range of Motion & Observations)
elif st.session_state.step == 9:
    st.title("턱 운동 범위 및 관찰 (Range of Motion & Observations)")
    st.markdown("---")
    st.markdown(
        "<span style='color:red;'>아래 항목은 실제 측정 및 검사가 필요할 수 있으며, 가능하신 부분만 기입해 주시면 됩니다. 나머지는 진료 중 확인할 수 있습니다.</span>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown("---")
        st.subheader("턱 움직임 패턴 (Mandibular Movement Pattern)")
        st.markdown("**입을 벌리고 닫을 때 턱이 한쪽으로 치우치는 것 같나요?**")
        st.radio(
            label=" ",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("deviation", "선택 안 함")),
            key="deviation_widget",
            on_change=sync_widget_key,
            args=("deviation_widget", "deviation"),
            label_visibility="collapsed"
        )
        st.markdown("**편위(Deviation, 치우치지만 마지막에는 중앙으로 돌아옴)**")
        st.radio(
            label=" ",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("deviation2", "선택 안 함")),
            key="deviation2_widget",
            on_change=sync_widget_key,
            args=("deviation2_widget", "deviation2"),
            label_visibility="collapsed"
        )
        st.markdown("**편향(Deflection, 치우친 채 돌아오지 않음)**")
        st.radio(
            label="편향(Deflection): 치우치고 돌아오지 않음",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("deflection", "선택 안 함")),
            key="deflection_widget",
            on_change=sync_widget_key,
            args=("deflection_widget", "deflection"),
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**앞으로 내밀기(Protrusion) ______ mm (의료진이 측정 후 기록)**")
        st.text_input(
            label="",
            key="protrusion_widget",
            value=st.session_state.get("protrusion", ""),
            on_change=sync_widget_key,
            args=("protrusion_widget", "protrusion"),
            label_visibility="collapsed"
        )

        st.radio(
            "**Protrusion 시 통증 여부**",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("protrusion_pain", "선택 안 함")),
            key="protrusion_pain_widget",
            on_change=sync_widget_key,
            args=("protrusion_pain_widget", "protrusion_pain")
        )

        st.markdown("---")
        st.markdown("**측방운동(Laterotrusion) 오른쪽: ______ mm (의료진이 측정 후 기록)**")
        st.text_input(
            label="",
            key="latero_right_widget",
            value=st.session_state.get("latero_right", ""),
            on_change=sync_widget_key,
            args=("latero_right_widget", "latero_right"),
            label_visibility="collapsed"
        )

        st.radio(
            "**Laterotrusion 오른쪽 통증 여부**",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("latero_right_pain", "선택 안 함")),
            key="latero_right_pain_widget",
            on_change=sync_widget_key,
            args=("latero_right_pain_widget", "latero_right_pain")
        )

        st.markdown("---")
        st.markdown("**측방운동(Laterotrusion) 왼쪽: ______ mm (의료진이 측정 후 기록)**")
        st.text_input(
            label="",
            key="latero_left_widget",
            value=st.session_state.get("latero_left", ""),
            on_change=sync_widget_key,
            args=("latero_left_widget", "latero_left"),
            label_visibility="collapsed"
        )

        st.radio(
            "**Laterotrusion 왼쪽 통증 여부**",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("latero_left_pain", "선택 안 함")),
            key="latero_left_pain_widget",
            on_change=sync_widget_key,
            args=("latero_left_pain_widget", "latero_left_pain")
        )

        st.markdown("---")
        st.markdown("**교합(Occlusion): 앞니(위, 아래)가 정중앙에서 잘 맞물리나요?**")
        st.radio(
            label="",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("occlusion", "선택 안 함")),
            key="occlusion_widget",
            on_change=sync_widget_key,
            args=("occlusion_widget", "occlusion"),
            label_visibility="collapsed"
        )

        if st.session_state.get("occlusion") == "아니오":
            st.markdown("**정중앙이 어느 쪽으로 어긋나는지:**")
            shift_value = st.session_state.get("occlusion_shift", "선택 안 함")
            shift_options = ["오른쪽", "왼쪽", "선택 안 함"]
            shift_index = shift_options.index(shift_value) if shift_value in shift_options else 2

            st.radio(
                label="",
                options=shift_options,
                index=shift_index,
                key="occlusion_shift_widget",
                on_change=sync_widget_key,
                args=("occlusion_shift_widget", "occlusion_shift"),
                label_visibility="collapsed"
            )
        else:
            st.session_state["occlusion_shift"] = ""

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 8
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            sync_multiple_keys({
                "deviation_widget": "deviation",
                "deviation2_widget": "deviation2",
                "deflection_widget": "deflection",
                "protrusion_widget": "protrusion",
                "protrusion_pain_widget": "protrusion_pain",
                "latero_right_widget": "latero_right",
                "latero_right_pain_widget": "latero_right_pain",
                "latero_left_widget": "latero_left",
                "latero_left_pain_widget": "latero_left_pain",
                "occlusion_widget": "occlusion",
                "occlusion_shift_widget": "occlusion_shift"
            })
            st.session_state.step = 10
            st.rerun()


# STEP 10: 턱 운동 범위 및 관찰3 (Range of Motion & Observations)
elif st.session_state.step == 10:
    st.title("턱 운동 범위 및 관찰 (Range of Motion & Observations)")
    st.markdown("---")
    st.markdown(
        "<span style='color:red;'>아래 항목은 실제 측정 및 검사가 필요할 수 있으며, 가능하신 부분만 기입해 주시면 됩니다. 나머지는 진료 중 확인할 수 있습니다.</span>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown("---")
        st.subheader("턱관절 소리 (TMJ Noise)")

        # 오른쪽 - 입 벌릴 때
        st.markdown("**오른쪽 - 입 벌릴 때**")
        st.radio(
            label="", 
            options=["딸깍/소리", "없음", "선택 안 함"],
            index=["딸깍/소리", "없음", "선택 안 함"].index(
                st.session_state.get("tmj_noise_right_open", "선택 안 함")
            ),
            key="tmj_noise_right_open_widget",
            on_change=sync_widget_key,
            args=("tmj_noise_right_open_widget", "tmj_noise_right_open"),
            label_visibility="collapsed"
        )
       

        # 왼쪽 - 입 벌릴 때
        st.markdown("---")
        st.markdown("**왼쪽 - 입 벌릴 때**")
        st.radio(
            label="", 
            options=["딸깍/소리", "없음", "선택 안 함"],
            index=["딸깍/소리", "없음", "선택 안 함"].index(
                st.session_state.get("tmj_noise_left_open", "선택 안 함")
            ),
            key="tmj_noise_left_open_widget",
            on_change=sync_widget_key,
            args=("tmj_noise_left_open_widget", "tmj_noise_left_open"),
            label_visibility="collapsed"
        )
        

        # 오른쪽 - 입 다물 때
        st.markdown("---")
        st.markdown("**오른쪽 - 입 다물 때**")
        st.radio(
            label="", 
            options=["딸깍/소리", "없음", "선택 안 함"],
            index=["딸깍/소리", "없음", "선택 안 함"].index(
                st.session_state.get("tmj_noise_right_close", "선택 안 함")
            ),
            key="tmj_noise_right_close_widget",
            on_change=sync_widget_key,
            args=("tmj_noise_right_close_widget", "tmj_noise_right_close"),
            label_visibility="collapsed"
        )
       

        # 왼쪽 - 입 다물 때
        st.markdown("---")
        st.markdown("**왼쪽 - 입 다물 때**")
        st.radio(
            label="", 
            options=["딸깍/소리", "없음", "선택 안 함"],
            index=["딸깍/소리", "없음", "선택 안 함"].index(
                st.session_state.get("tmj_noise_left_close", "선택 안 함")
            ),
            key="tmj_noise_left_close_widget",
            on_change=sync_widget_key,
            args=("tmj_noise_left_close_widget", "tmj_noise_left_close"),
            label_visibility="collapsed"
        )
        

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 9
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            st.session_state.step = 11
            st.rerun()




# STEP 11: 근육 촉진 평가
elif st.session_state.step == 11:
    st.title("근육 촉진 평가")
    st.markdown("---")

    with st.container(border=True):
        st.markdown(
            "<span style='color:red;'>아래 항목은 검사가 필요한 항목으로, 진료 중 확인할 수 있습니다.</span>",
            unsafe_allow_html=True
        )
        st.markdown("### 의료진 촉진 소견")

        palpation_fields = [
            ("측두근 촉진 소견", "palpation_temporalis_widget", "palpation_temporalis"),
            ("내측 익돌근 촉진 소견", "palpation_medial_pterygoid_widget", "palpation_medial_pterygoid"),
            ("외측 익돌근 촉진 소견", "palpation_lateral_pterygoid_widget", "palpation_lateral_pterygoid"),
            ("통증 위치 매핑 (지도 또는 상세 설명)", "pain_mapping_widget", "pain_mapping"),
        ]

        image_files_in_order = ["temporalis.jpg", "medial.jpg", "lateral.jpg"]

        for idx, (label, widget_key, session_key) in enumerate(palpation_fields):
            st.markdown(f"**{label}**")

            if idx < len(image_files_in_order):
                # 1~3번째: 사진 + 가로 배치
                col1, col2 = st.columns([1, 2])

                with col1:
                    img_path = os.path.join(script_dir, image_files_in_order[idx])
                    if os.path.exists(img_path):
                        st.image(img_path, width=300)

                with col2:
                    st.text_area(
                        label=label,
                        key=widget_key,
                        value=st.session_state.get(session_key, ""),
                        on_change=sync_widget_key,
                        args=(widget_key, session_key),
                        placeholder="검사가 필요한 항목입니다.",
                        label_visibility="collapsed",
                        height=300  # 사진과 높이 맞춤
                    )
            else:
                # 마지막: 기본 입력창만
                st.text_area(
                    label=label,
                    key=widget_key,
                    value=st.session_state.get(session_key, ""),
                    on_change=sync_widget_key,
                    args=(widget_key, session_key),
                    placeholder="검사가 필요한 항목입니다.",
                    label_visibility="collapsed"
                )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 10
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            sync_multiple_keys({
                "palpation_temporalis_widget": "palpation_temporalis",
                "palpation_medial_pterygoid_widget": "palpation_medial_pterygoid",
                "palpation_lateral_pterygoid_widget": "palpation_lateral_pterygoid",
                "pain_mapping_widget": "pain_mapping",
            }) 
            st.session_state.step = 12
            st.rerun()

# STEP 12: 귀 관련 증상
elif st.session_state.step == 12:
    st.title("귀 관련 증상")
    st.markdown("---")

    with st.container(border=True):
        st.markdown("**다음 중 귀와 관련된 증상이 있으신가요?**")

        ear_symptoms = [
            "이명 (귀울림)", "귀가 먹먹한 느낌", "귀 통증", "청력 저하"
        ]

        # 상태 초기화
        st.session_state.setdefault("selected_ear_symptoms", [])
        st.session_state.setdefault("ear_symptom_other", "")

        # 없음 체크 박스
        def toggle_ear_symptom_none():
            if st.session_state.ear_symptom_none:
                st.session_state.selected_ear_symptoms = ["없음"]
            elif "없음" in st.session_state.selected_ear_symptoms:
                st.session_state.selected_ear_symptoms.remove("없음")

        st.checkbox(
            "없음",
            key="ear_symptom_none",
            value="없음" in st.session_state.selected_ear_symptoms,
            on_change=toggle_ear_symptom_none
        )

        disabled = "없음" in st.session_state.selected_ear_symptoms

        # 체크박스 렌더링
        for symptom in ear_symptoms:
            key = f"ear_symptom_{symptom}"
            default = symptom in st.session_state.selected_ear_symptoms

            def make_callback(s=symptom):
                def cb():
                    if st.session_state.get(f"ear_symptom_{s}"):
                        if s not in st.session_state.selected_ear_symptoms:
                            st.session_state.selected_ear_symptoms.append(s)
                    else:
                        if s in st.session_state.selected_ear_symptoms:
                            st.session_state.selected_ear_symptoms.remove(s)
                return cb

            st.checkbox(
                symptom,
                key=key,
                value=default,
                disabled=disabled,
                on_change=make_callback()
            )

     

    # 이전/다음 버튼
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 11
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            symptoms = st.session_state.get("selected_ear_symptoms", [])
            if not symptoms:
                st.warning("귀 관련 증상을 한 가지 이상 선택하거나 '없음'을 선택해주세요.")
            elif "없음" in symptoms and len(symptoms) > 1:
                st.warning("'없음'과 다른 증상을 동시에 선택할 수 없습니다. 다시 확인해주세요.")
            else:
                st.session_state.step = 13
                st.rerun()

elif st.session_state.step == 13:
    st.title("경추/목/어깨 관련 증상")
    st.markdown("---")

    # 1) 경추/목/어깨 증상 (multiselect)
    with st.container(border=True):
        st.markdown("**다음 중 경추/목/어깨 증상이 있으신가요? (복수 선택 가능)**")
        opts = list(DEFAULT_SYMPTOMS.keys())
        default_sel = [
            k for k, v in st.session_state[DATA_KEY].items() if v
        ]
        selected = st.multiselect(
            "증상 선택",
            options=opts,
            default=default_sel
        )
        # 세션에 다시 저장
        st.session_state[DATA_KEY] = {opt: (opt in selected) for opt in opts}

    st.markdown("---")

    # 2) 추가 증상 (multiselect)
    with st.container(border=True):
        st.markdown("**다음 중 추가 증상이 있다면 모두 선택해주세요.**")
        opts2 = list(DEFAULT_ADDS.keys())
        default2 = [
            k for k, v in st.session_state[ADD_KEY].items() if v
        ]
        sel2 = st.multiselect(
            "추가 증상 선택",
            options=opts2,
            default=default2
        )
        st.session_state[ADD_KEY] = {opt: (opt in sel2) for opt in opts2}

    st.markdown("---")

    # 3) 목 외상 이력 (radio)
    with st.container(border=True):
        st.markdown("**목 외상 관련 이력이 있으신가요?**")
        st.radio(
            "",
            options=["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(
                st.session_state.get("neck_trauma_radio", "선택 안 함")
            ),
            key="neck_trauma_radio_widget",
            on_change=sync_widget_key_with_auto_save,
            args=("neck_trauma_radio_widget", "neck_trauma_radio"),
            label_visibility="collapsed"
        )

    # 4) 이전/다음 버튼 & 검증
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀ 이전 단계"):
            st.session_state.step = 12
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 ▶"):
            trauma_ok = st.session_state.get("neck_trauma_radio") in ["예", "아니오"]
            symptoms_ok = any(st.session_state[DATA_KEY].values())

            if not symptoms_ok:
                st.warning("경추/목/어깨 증상에서 최소 하나를 선택해주세요.")
            elif not trauma_ok:
                st.warning("목 외상 여부를 선택해주세요.")
            else:
                st.session_state.step = 14
                st.rerun()


# STEP 14: 정서적 스트레스 이력
elif st.session_state.step == 14:
    st.title("정서적 스트레스 이력")
    st.markdown("---")

    with st.container(border=True):
        st.markdown("**스트레스, 불안, 우울감 등을 많이 느끼시나요?**")

        stress_options = ["예", "아니오", "선택 안 함"]
        st.radio(
            label="",
            options=stress_options,
            key="stress_radio_widget",  # 👈 위젯 key
            index=stress_options.index(st.session_state.get("stress_radio", "선택 안 함")),
            on_change=sync_widget_key,  # 👈 콜백
            args=("stress_radio_widget", "stress_radio"),
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**있다면 간단히 기재해 주세요:**")

        st.text_area(
            label="",
            key="stress_detail_widget",  # 👈 위젯 key
            value=st.session_state.get("stress_detail", ""),
            on_change=sync_widget_key,
            args=("stress_detail_widget", "stress_detail"),
            placeholder="예: 최근 업무 스트레스, 가족 문제 등",
            label_visibility="collapsed"
        )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 13
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            if st.session_state.get("stress_radio") == "선택 안 함":
                st.warning("스트레스 여부를 선택해주세요.")
            else:
                st.session_state.step = 15
                st.rerun()

                
# STEP 15: 과거 치과적 이력 (Past Dental History)

elif st.session_state.step == 15:
    st.title("과거 치과적 이력 (Past Dental History)")
    st.markdown("---")

    with st.container(border=True):
        # 교정치료 경험
        st.markdown("**교정치료(치아 교정) 경험**")
        ortho_options = ["예", "아니오", "선택 안 함"]
        st.radio(
            "", ortho_options,
            index=ortho_options.index(st.session_state.get("ortho_exp", "선택 안 함")),
            key="ortho_exp_widget", # 👈 위젯 키 변경
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("ortho_exp_widget", "ortho_exp"), # 👈 args 변경
            label_visibility="collapsed"
        )   

        st.text_input(
            "예라면 언제, 얼마나 받았는지 적어주세요:",
            key="ortho_detail_widget", # 👈 위젯 키 변경
            value=st.session_state.get("ortho_detail", ""),
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("ortho_detail_widget", "ortho_detail") # 👈 args 변경
            )
           

        st.markdown("---")

        # 보철치료 경험
        st.markdown("**보철치료(의치, 브리지, 임플란트 등) 경험**")
        prosth_options = ["예", "아니오", "선택 안 함"]
        st.radio(
            "", prosth_options,
            index=prosth_options.index(st.session_state.get("prosth_exp", "선택 안 함")),
            key="prosth_exp_widget", # 👈 위젯 키 변경
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("prosth_exp_widget", "prosth_exp"), # 👈 args 변경
            label_visibility="collapsed"
        )

        

        st.text_input(
            "예라면 어떤 치료였는지 적어주세요:",
            key="prosth_detail_widget", # 👈 위젯 키 변경
            value=st.session_state.get("prosth_detail", ""),
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("prosth_detail_widget", "prosth_detail") # 👈 args 변경
        )
        st.markdown("---")

        # 기타 치과 치료
        st.markdown("**기타 치과 치료 이력 (주요 치과 시술, 수술 등)**")
        st.text_area(
            "",
            key="other_dental_widget", # 👈 위젯 키 변경
            value=st.session_state.get("other_dental", ""),
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("other_dental_widget", "other_dental"), # 👈 args 변경
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 턱관절 치료 이력
        st.markdown("**이전에 턱관절 질환 치료를 받은 적 있나요?**")
        st.radio(
            "",
            ["예", "아니오", "선택 안 함"],
            index=["예", "아니오", "선택 안 함"].index(st.session_state.get("tmd_treatment_history", "선택 안 함")),
            key="tmd_treatment_history_widget", # 👈 위젯 키 변경
            on_change=sync_widget_key, # 👈 콜백 함수 변경
            args=("tmd_treatment_history_widget", "tmd_treatment_history"), # 👈 args 변경
            label_visibility="collapsed"
        )
        if st.session_state.get("tmd_treatment_history") == "예":
            st.text_input(
                "어떤 치료를 받으셨나요?",
                key="tmd_treatment_detail_widget",
                value=st.session_state.get("tmd_treatment_detail", ""),
                on_change=sync_widget_key,
                args=("tmd_treatment_detail_widget", "tmd_treatment_detail")
             )
            st.text_input(
                "해당 치료에 대한 반응(효과나 문제점 등):",
                key="tmd_treatment_response_widget",
                value=st.session_state.get("tmd_treatment_response", ""),
                on_change=sync_widget_key,
                args=("tmd_treatment_response_widget", "tmd_treatment_response")
            )
            st.text_input(
                "현재 복용 중인 턱관절 관련 약물이 있다면 입력해주세요:",
                key="tmd_current_medications_widget",
                value=st.session_state.get("tmd_current_medications", ""),
                on_change=sync_widget_key,
                args=("tmd_current_medications_widget", "tmd_current_medications")
            )
        else:
            st.session_state["tmd_treatment_detail"] = ""
            st.session_state["tmd_treatment_response"] = ""
            st.session_state["tmd_current_medications"] = ""

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 14
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            errors = []
            if st.session_state.get("ortho_exp") == "선택 안 함":
                errors.append("교정치료 경험 여부를 선택해주세요.")
            if st.session_state.get("prosth_exp") == "선택 안 함":
                errors.append("보철치료 경험 여부를 선택해주세요.")
            if st.session_state.get("tmd_treatment_history") == "선택 안 함":
                errors.append("턱관절 치료 경험 여부를 선택해주세요.")

            if errors:
                for e in errors:
                    st.warning(e)
            else:
                st.session_state.step = 16
                st.rerun()


# STEP 16: 과거 의과적 이력 (Past Medical History)
elif st.session_state.step == 16:
    st.title("과거 의과적 이력 (Past Medical History)")
    st.markdown("---")

    with st.container(border=True):
        
        st.markdown("**과거에 앓았던 질환, 입원 등 주요 의학적 이력이 있다면 적어주세요:**")
        st.text_area(
            label="",
            key="past_history_widget", # 위젯 키
            value=st.session_state.get("past_history", ""), # 세션 상태 키
            on_change=sync_widget_key,
            args=("past_history_widget", "past_history"),
            label_visibility="collapsed"
        )


        st.markdown("---")
        st.markdown("**현재 복용 중인 약이 있다면 적어주세요:**")
        st.text_area(
            label="",
            key="current_medications_widget", # 위젯 키
            value=st.session_state.get("current_medications", ""), # 세션 상태 키
            on_change=sync_widget_key,
            args=("current_medications_widget", "current_medications"),
            label_visibility="collapsed"
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 15
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            st.session_state.step = 17
            st.rerun()

  
# STEP 17: 자극 검사
elif st.session_state.step == 17:
    st.title("자극 검사 (Provocation Tests)")
    st.markdown("---")

    st.markdown(
        "<span style='color:red;'>아래 항목은 실제 측정 및 검사가 필요할 수 있으며, 가능하신 부분만 기입해 주시면 됩니다.</span>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown("**오른쪽으로 어금니를 강하게 물 때:**")
        st.radio(
            label="",
            options=["통증 있음", "통증 없음", "선택 안 함"],
            key="bite_right_widget", # 위젯 키
            index=["통증 있음", "통증 없음", "선택 안 함"].index(st.session_state.get("bite_right", "선택 안 함")),
            on_change=sync_widget_key,
            args=("bite_right_widget", "bite_right"), # 최종 저장 키
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**왼쪽으로 어금니를 강하게 물 때:**")
        st.radio(
            label="",
            options=["통증 있음", "통증 없음", "선택 안 함"],
            key="bite_left_widget", # 위젯 키
            index=["통증 있음", "통증 없음", "선택 안 함"].index(st.session_state.get("bite_left", "선택 안 함")),
            on_change=sync_widget_key,
            args=("bite_left_widget", "bite_left"), # 최종 저장 키
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**압력 가하기 (Loading Test):**")
        st.radio(
            label="",
            options=["통증 있음", "통증 없음", "선택 안 함"],
            key="loading_test_widget",
            index=["통증 있음", "통증 없음", "선택 안 함"].index(st.session_state.get("loading_test", "선택 안 함")),
            on_change=sync_widget_key,
            args=("loading_test_widget", "loading_test"),
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**저항 검사 (Resistance Test, 턱 움직임 막기):**")
        st.radio(
            label="",
            options=["통증 있음", "통증 없음", "선택 안 함"],
            key="resistance_test_widget",
            index=["통증 있음", "통증 없음", "선택 안 함"].index(st.session_state.get("resistance_test", "선택 안 함")),
            on_change=sync_widget_key,
            args=("resistance_test_widget", "resistance_test"),
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("**치아 마모 (Attrition)**")
        st.radio(
            label="",
            options=["경미", "중간", "심함", "선택 안 함"],
            key="attrition_widget", # 위젯 키를 명확히 구분
            index=["경미", "중간", "심함", "선택 안 함"].index(st.session_state.get("attrition", "선택 안 함")),
            on_change=sync_widget_key,
            args=("attrition_widget", "attrition"),
            label_visibility="collapsed"
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 16
            st.rerun()

    with col2:
        if st.button("다음 단계로 이동 👉"):
            st.session_state.step = 18
            st.rerun()

# STEP 18: 기능 평가
elif st.session_state.step == 18:
    st.title("기능 평가 (Functional Impact)")
    st.markdown("---")

    # 1) 일상생활 영향
    st.markdown("**턱관절 증상으로 인해 일상생활(음식 섭취, 말하기, 하품 등)에 불편함을 느끼시나요?**")
    daily_opts = [
        "전혀 불편하지 않음", "약간 불편함", "자주 불편함",
        "매우 불편함", "선택 안 함"
    ]
    st.radio(
        "",
        daily_opts,
        index=daily_opts.index(
            st.session_state.get("impact_daily", "선택 안 함")
        ),
        key="impact_daily_widget",
        on_change=sync_widget_key_with_auto_save,
        args=("impact_daily_widget", "impact_daily"),
        label_visibility="collapsed"
    )

    st.markdown("---")


    # 2) 직장/학교 영향
    st.markdown("**턱관절 증상으로 인해 직장 업무나 학업 성과에 영향을 받은 적이 있나요?**")    
    work_opts = [
        "전혀 영향 없음",
        "약간 집중에 어려움 있음",
        "자주 집중이 힘들고 성과 저하 경험",
        "매우 큰 영향으로 일/학업 중단 고려한 적 있음",
        "선택 안 함"
    ]
    st.radio(
        "",
        work_opts,
        index=work_opts.index(
            st.session_state.get("impact_work", "선택 안 함")
        ),
        key="impact_work_widget",
        on_change=sync_widget_key_with_auto_save,
        args=("impact_work_widget", "impact_work"),
        label_visibility="collapsed"
    )

    st.markdown("---")

    # 3) 삶의 질 영향
    st.markdown("**턱관절 증상이 귀하의 전반적인 삶의 질에 얼마나 영향을 미치고 있다고 느끼시나요?**")    
    quality_opts = [
        "전혀 영향을 미치지 않음",
        "약간 영향을 미침",
        "영향을 많이 받음",
        "심각하게 삶의 질 저하",
        "선택 안 함"
    ]
    st.radio(
        "",
        quality_opts,
        index=quality_opts.index(
            st.session_state.get("impact_quality_of_life", "선택 안 함")
        ),
        key="impact_quality_widget",
        on_change=sync_widget_key_with_auto_save,
        args=("impact_quality_widget", "impact_quality_of_life"),
        label_visibility="collapsed"
    )

    st.markdown("---")

    # 4) 수면의 질
    st.markdown("**최근 2주간 수면의 질은 어떠셨나요?**")    
    sleep_opts = ["좋음", "보통", "나쁨", "매우 나쁨", "선택 안 함"]
    st.radio(
        "",
        sleep_opts,
        index=sleep_opts.index(
            st.session_state.get("sleep_quality", "선택 안 함")
        ),
        key="sleep_quality_widget",
        on_change=sync_widget_key_with_auto_save,
        args=("sleep_quality_widget", "sleep_quality"),
        label_visibility="collapsed"
    )

    st.markdown("---")

    # 5) 수면↔턱관절 연관성
    st.markdown("**수면의 질이 턱관절 증상(통증, 근육 경직 등)에 영향을 준다고 느끼시나요?**")    
    relation_opts = ["영향을 미침", "영향을 미치지 않음", "잘 모르겠음", "선택 안 함"]
    st.radio(
        "",
        relation_opts,
        index=relation_opts.index(
            st.session_state.get("sleep_tmd_relation", "선택 안 함")
        ),
        key="sleep_relation_widget",
        on_change=sync_widget_key_with_auto_save,
        args=("sleep_relation_widget", "sleep_tmd_relation"),
        label_visibility="collapsed"
    )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("이전 단계"):
            st.session_state.step = 17
            st.rerun()

    with col2:
        if st.button("제출 👉"):
            errors = []
            if st.session_state.get("impact_daily") == "선택 안 함":
                errors.append("일상생활 영향 여부를 선택해주세요.")
            # … 그 외 validation …

            if errors:
                for err in errors:
                    st.warning(err)
            else:
                save_session()                      # ← 최종 저장
                st.session_state.step = 19
                st.rerun()


# STEP 19: 결과
elif st.session_state.step == 19:
    st.title("📊 턱관절 질환 예비 진단 결과")
    st.markdown("---")
    results = compute_diagnoses(st.session_state)
    st.session_state["diagnosis_result"] = ", ".join(results) if results else "진단 없음"
    dc_tmd_explanations = {
        "근육통 (Myalgia)": "턱 주변 근육에서 발생하는 통증으로, 움직임이나 압박 시 통증이 심해지는 증상입니다.",
        "국소 근육통 (Local Myalgia)": "통증이 특정 근육 부위에만 국한되어 있고, 다른 부위로 퍼지지 않는 증상입니다.",
        "방사성 근막통 (Myofascial Pain with Referral)": "특정 근육을 눌렀을 때 통증이 다른 부위로 방사되어 퍼지는 증상입니다.",
        "관절통 (Arthralgia)": "턱관절 자체에 발생하는 통증으로, 움직이거나 누를 때 통증이 유발되는 상태입니다.",
        "퇴행성 관절 질환 (Degenerative Joint Disease)": "턱관절의 연골이나 뼈가 마모되거나 손상되어 통증과 기능 제한이 동반되는 상태입니다.",
        "비정복성 관절원판 변위, 개구 제한 없음 (Disc Displacement without Reduction)": "턱관절 디스크가 비정상 위치에 있으며, 입을 벌려도 제자리로 돌아오지 않는 상태입니다.",
        "비정복성 관절원판 변위, 개구 제한 동반 (Disc Displacement without Reduction with Limited opening)": "디스크가 제자리로 돌아오지 않으며, 입 벌리기가 제한되는 상태입니다.",
        "정복성 관절원판 변위, 간헐적 개구 장애 동반 (Disc Displacement with reduction, with intermittent locking)": "디스크가 움직일 때 딸깍소리가 나며, 일시적인 입 벌리기 장애가 간헐적으로 나타나는 상태입니다.",
        "정복성 관절원판 변위 (Disc Displacement with Reduction)": "입을 벌릴 때 디스크가 제자리로 돌아오며 딸깍소리가 나는 상태이며, 기능 제한은 없는 경우입니다.",
        "TMD에 기인한 두통 (Headache attributed to TMD)": "턱관절 또는 턱 주변 근육 문제로 인해 발생하는 두통으로, 턱을 움직이거나 근육을 누르면 증상이 악화되는 경우입니다."
    }
    if not results:
        st.success("✅ DC/TMD 기준상 명확한 진단 근거는 확인되지 않았습니다.\n\n다른 질환 가능성에 대한 조사가 필요합니다.")
    else:
        st.session_state["diagnosis_result"] = ", ".join(results)
        if len(results) == 1:
            st.error(f"**{results[0]}**이(가) 의심됩니다.")
        else:
            st.error(f"**{', '.join(results)}**이(가) 의심됩니다.")
        st.markdown("---")
        for diagnosis in results:
            st.markdown(f"### 🔹 {diagnosis}")
            st.info(dc_tmd_explanations.get(diagnosis, "설명 없음"))
            st.markdown("---")
    st.info("※ 본 결과는 예비 진단이며, 전문의 상담을 반드시 권장합니다.")
	

    # ✅ 여기에 파일 업로더를 추가합니다.
    st.markdown("---")
    st.subheader("📸 증빙자료 첨부 (선택 사항)")
    st.info("X-ray, 파노라마 사진 등 관련 자료가 있다면 PDF 보고서에 함께 첨부할 수 있습니다.")
    
    # st.session_state에 업로드된 파일 목록을 저장합니다.
    st.session_state.uploaded_images = st.file_uploader(
        "이미지 파일을 선택하세요 (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="evidence_uploader"
    )


    if st.button("처음으로 돌아가기", use_container_width=True):
        st.session_state.step = 0
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()



import datetime

# 진단 결과가 없을 경우 기본값 설정
if "diagnosis_result" not in st.session_state:
    result = compute_diagnoses(st.session_state)
    st.session_state["diagnosis_result"] = ", ".join(result) if result else "진단 없음"

# 마지막 단계에서 PDF 다운로드 버튼 노출
if st.session_state.get("step") == final_step:
    # PDF 다운로드 버튼 렌더링
    if st.download_button(
        label="📥 진단 결과 PDF 다운로드",
        data=generate_filled_pdf(),
        file_name=f"턱관절_진단_결과_{datetime.date.today()}.pdf",
        mime="application/pdf"
    ):
        pass





