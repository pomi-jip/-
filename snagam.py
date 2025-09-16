
import streamlit as st
import requests
import datetime
import pytz
import json
import re
import pandas as pd
import streamlit.components.v1 as components
from typing import List, Dict, Any
import logging
import random

# ====== 기본 세팅 ======
st.set_page_config(
    page_title="🍱 상암고 급식 캘린더", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS (초록-하얀 테마)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    .main > div {
        padding-top: 2rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        border-radius: 20px;
        padding: 10px;
        box-shadow: 0 8px 32px rgba(27, 94, 32, 0.37);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: white;
        font-weight: 600;
        border-radius: 15px;
        padding: 12px 24px;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .meal-card {
        background: linear-gradient(145deg, #ffffff, #f1f8e9);
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 10px 30px rgba(46, 125, 50, 0.15);
        border: 1px solid rgba(139, 195, 74, 0.3);
        transition: all 0.3s ease;
    }
    
    .meal-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(46, 125, 50, 0.25);
        border-color: rgba(76, 175, 80, 0.5);
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    .info-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 25px rgba(255, 152, 0, 0.15);
        border-left: 5px solid #ff9800;
    }
    
    .success-box {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c8 100%);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 5px 20px rgba(46, 125, 50, 0.2);
        border-left: 5px solid #4caf50;
    }
    
    .search-container {
        background: linear-gradient(135deg, #e8f5e8 0%, #dcedc8 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 8px 25px rgba(46, 125, 50, 0.15);
        border: 1px solid rgba(139, 195, 74, 0.3);
    }
    
    .stat-card {
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        min-width: 150px;
        box-shadow: 0 8px 25px rgba(46, 125, 50, 0.3);
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(46, 125, 50, 0.4);
    }
    
    .game-card {
        background: linear-gradient(145deg, #fff3e0, #ffe0b2);
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 10px 30px rgba(255, 152, 0, 0.15);
        border: 1px solid rgba(255, 193, 7, 0.3);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .game-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(255, 152, 0, 0.25);
        border-color: rgba(255, 193, 7, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 시간대 및 날짜 설정
KST = pytz.timezone("Asia/Seoul")
TODAY = datetime.datetime.now(KST)

# 상수 정의
ALLERGY_MAP = {
    "1": "난류(계란)", "2": "우유", "3": "메밀", "4": "땅콩", "5": "대두",
    "6": "밀", "7": "고등어", "8": "게", "9": "새우", "10": "돼지고기",
    "11": "복숭아", "12": "토마토", "13": "아황산류", "14": "호두",
    "15": "닭고기", "16": "쇠고기", "17": "오징어", "18": "조개류"
}

API_KEY = "63d5c778631448b4823ab83abdfe9957"
ATPT_OFCDC_SC_CODE = "B10"
SD_SCHUL_CODE = "7010806"

# ====== 캐싱 및 성능 개선 ======
@st.cache_data(ttl=3600)
def get_cached_meals() -> List[Dict[str, Any]]:
    """급식 데이터를 캐시와 함께 가져오는 함수"""
    return get_meals()

# ====== 칼로리 추정 함수 ======
def estimate_calories(meal_text: str) -> int:
    """급식 메뉴를 기반으로 칼로리를 추정하는 함수"""
    # 메뉴별 대략적인 칼로리 추정
    calorie_keywords = {
        "밥": 150, "쌀": 150, "현미": 140, "잡곡": 160,
        "김치찌개": 120, "된장찌개": 100, "미역국": 30, "콩나물국": 25,
        "불고기": 180, "닭고기": 165, "생선": 120, "돼지고기": 200,
        "계란": 70, "두부": 80, "콩": 60,
        "김치": 20, "샐러드": 50, "나물": 30, "무": 15,
        "우유": 60, "요구르트": 80,
        "빵": 250, "떡": 200, "면": 180,
        "튀김": 200, "전": 150, "볶음": 120
    }
    
    total_calories = 0
    meal_lower = meal_text.lower().replace(" ", "")
    
    # 키워드 매칭으로 칼로리 합산
    for keyword, calories in calorie_keywords.items():
        if keyword in meal_lower:
            total_calories += calories
    
    # 메뉴 개수 기반 보정
    menu_items = [item.strip() for item in meal_text.replace("🍽", "").split("\n") if item.strip()]
    menu_count = len(menu_items)
    
    # 기본 칼로리가 너무 낮으면 메뉴 개수로 추정
    if total_calories < 200:
        total_calories = 200 + (menu_count - 1) * 80
    
    # 일반적인 학교급식 칼로리 범위로 제한
    return min(max(total_calories, 450), 850)

# ====== 급식 파싱 함수 개선 ======
def parse_meal_text(meal_str: str) -> str:
    """급식 텍스트를 파싱하여 알레르기 정보와 함께 포맷팅"""
    if not meal_str:
        return "급식 정보가 없습니다."
    
    result = []
    for line in meal_str.split("<br/>"):
        line = line.strip()
        if not line:
            continue
            
        match = re.match(r"(.+?)([\d,\.\s]+)$", line)
        if match:
            food = match.group(1).strip()
            allergy_codes = re.findall(r"\d+", match.group(2))
            allergy_list = [ALLERGY_MAP[code] for code in allergy_codes if code in ALLERGY_MAP]
            
            if allergy_list:
                result.append(f"🍽 {food} <span style='color:#d84315; font-weight:500;'>({', '.join(allergy_list)})</span>")
            else:
                result.append(f"🍽 {food}")
        else:
            result.append(f"🍽 {line}")
    
    return "<br>".join(result) if result else "급식 정보가 없습니다."

def get_meals() -> List[Dict[str, Any]]:
    """NEIS API에서 급식 데이터를 가져오는 함수"""
    try:
        start_date = (TODAY - datetime.timedelta(days=30)).strftime("%Y%m%d")
        end_date = (TODAY + datetime.timedelta(days=31)).strftime("%Y%m%d")
        
        url = (f"https://open.neis.go.kr/hub/mealServiceDietInfo"
               f"?KEY={API_KEY}&Type=json&pIndex=1&pSize=500"
               f"&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
               f"&SD_SCHUL_CODE={SD_SCHUL_CODE}"
               f"&MLSV_FROM_YMD={start_date}&MLSV_TO_YMD={end_date}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "mealServiceDietInfo" not in data or len(data["mealServiceDietInfo"]) < 2:
            return []
        
        meal_data = data["mealServiceDietInfo"][1]["row"]
        events = []
        
        for row in meal_data:
            try:
                date = row["MLSV_YMD"]
                formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                meals_text = parse_meal_text(row["DDISH_NM"].replace(" ", "").replace("\r", ""))
                
                # 칼로리 정보가 있으면 사용, 없으면 추정
                calories = 0
                if "CAL_INFO" in row and row["CAL_INFO"]:
                    try:
                        # API에서 칼로리 정보 파싱 (예: "650.5 Kcal" -> 651)
                        cal_match = re.search(r'(\d+(?:\.\d+)?)', row["CAL_INFO"])
                        if cal_match:
                            calories = int(float(cal_match.group(1)))
                    except:
                        pass
                
                # 칼로리 정보가 없으면 추정
                if calories == 0:
                    clean_meal_text = re.sub('<.*?>', '', meals_text)
                    calories = estimate_calories(clean_meal_text)
                
                events.append({
                    "title": f"🍴 급식 ({calories}kcal)",
                    "start": formatted_date,
                    "extendedProps": {
                        "description": meals_text,
                        "calories": calories,
                        "raw_date": date
                    }
                })
            except KeyError:
                continue
        
        return events
    except Exception as e:
        logger.error(f"데이터 로딩 오류: {e}")
        return []

def main():
    # 아름다운 헤더 (초록 테마)
    st.markdown(f"""
        <div style='text-align:center; margin: 2rem 0 3rem 0; padding: 2rem;
                    background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
                    border-radius: 25px; box-shadow: 0 15px 35px rgba(46, 125, 50, 0.3);'>
            <h1 style='color: white; font-size: 3.5rem; font-weight: 700; 
                       text-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 0.5rem;
                       font-family: "Noto Sans KR", sans-serif;'>
                🍱 상암고등학교 급식 캘린더
            </h1>
            <p style='color: rgba(255,255,255,0.9); font-size: 1.3rem; margin: 0;
                      font-weight: 300; text-shadow: 0 2px 8px rgba(0,0,0,0.2);'>
                🌱 매일매일 건강하고 맛있는 우리 학교 급식을 확인해보세요! 🌱
            </p>
            <div style='margin-top: 1.5rem; display: flex; justify-content: center; gap: 2rem;'>
                <div style='background: rgba(255,255,255,0.2); padding: 0.8rem 1.5rem; 
                           border-radius: 50px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 500;'>📅 {TODAY.strftime("%Y년 %m월 %d일")}</span>
                </div>
                <div style='background: rgba(255,255,255,0.2); padding: 0.8rem 1.5rem; 
                           border-radius: 50px; backdrop-filter: blur(10px);'>
                    <span style='color: white; font-weight: 500;'>🏫 상암고등학교</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 로딩 애니메이션
    with st.spinner("🔄 맛있는 급식 데이터를 불러오는 중..."):
        events = get_cached_meals()
    
    # 통계 정보
    if events:
        col1, col2, col3, col4 = st.columns(4)
        
        # 평균 칼로리 계산
        avg_calories = int(sum(event['extendedProps']['calories'] for event in events) / len(events))
        
        with col1:
            st.markdown(f"""
            <div class='stat-card'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>📊</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{len(events)}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>총 급식 일수</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='stat-card'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🔥</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{avg_calories}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>평균 칼로리</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            today_meal = next((e for e in events if e['start'] == TODAY.strftime('%Y-%m-%d')), None)
            status = "✅ 있음" if today_meal else "❌ 없음"
            st.markdown(f"""
            <div class='stat-card'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>📅</div>
                <div style='font-size: 1.2rem; font-weight: bold;'>{status}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>오늘 급식</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class='stat-card'>
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🎮</div>
                <div style='font-size: 1.2rem; font-weight: bold;'>NEW!</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>미니게임</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin: 0 0 10px 0; color: #1b5e20;'>🎉 데이터 로딩 완료!</h3>
            <p style='margin: 0; color: #2e7d32; font-size: 1.1rem;'>
                총 <strong>{len(events)}일</strong>의 맛있는 급식 정보를 성공적으로 불러왔습니다!
                평균 칼로리: <strong>{avg_calories}kcal</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='info-box'>
            <h3 style='margin: 0 0 10px 0; color: #e65100;'>⚠️ 데이터 로딩 실패</h3>
            <p style='margin: 0; color: #ff6f00;'>
                급식 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["📅 급식 캘린더", "📋 급식 목록", "🎮 미니게임", "ℹ️ 학교 정보"])
    
    with tab1:
        create_green_calendar(events)
    
    with tab2:
        create_beautiful_meal_list(events)
    
    with tab3:
        create_mini_games(events)
    
    with tab4:
        create_school_info()

def create_green_calendar(events: List[Dict[str, Any]]):
    """초록 테마 캘린더 UI 생성 (칼로리 정보 포함)"""
    events_json = json.dumps(events, ensure_ascii=False)
    
    calendar_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet'>
    </head>
    <body>
        <div id='calendar-container' style='margin: 1rem 0; position: relative;'>
            <div id='calendar' style="border-radius: 20px; overflow: hidden; 
                                      background: white; box-shadow: 0 15px 35px rgba(46, 125, 50, 0.2);
                                      border: 2px solid #81c784;"></div>
        </div>
        
        <button id="fireworksBtn" style="position: fixed; bottom: 30px; right: 30px; z-index: 9999;
                                      background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
                                      color: white; border: none; border-radius: 50%; 
                                      width: 70px; height: 70px; font-size: 24px; cursor: pointer; 
                                      box-shadow: 0 8px 25px rgba(46, 125, 50, 0.4);
                                      transition: all 0.3s ease;"
               onmouseover="this.style.transform='scale(1.1) rotate(10deg)'"
               onmouseout="this.style.transform='scale(1) rotate(0deg)'">
            🎆
        </button>

        <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
        <script src='https://cdn.jsdelivr.net/npm/sweetalert2@11'></script>
        <script src='https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js'></script>

        <style>
            .fc {{
                font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            
            .fc-header-toolbar {{
                background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
                padding: 15px 20px !important;
                margin-bottom: 0 !important;
                border-radius: 20px 20px 0 0;
            }}
            
            .fc-toolbar-title {{
                color: white !important;
                font-size: 1.8rem !important;
                font-weight: 600 !important;
            }}
            
            .fc-button {{
                background: rgba(255,255,255,0.2) !important;
                border: 1px solid rgba(255,255,255,0.3) !important;
                color: white !important;
                border-radius: 12px !important;
                padding: 8px 16px !important;
                font-weight: 500 !important;
                transition: all 0.3s ease !important;
            }}
            
            .fc-button:hover {{
                background: rgba(255,255,255,0.3) !important;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            
            .fc-button:focus {{
                box-shadow: 0 0 0 0.2rem rgba(139, 195, 74, 0.5) !important;
            }}
            
            .fc-button-primary:not(:disabled):active,
            .fc-button-primary:not(:disabled).fc-button-active {{
                background: rgba(255,255,255,0.4) !important;
                border-color: rgba(255,255,255,0.4) !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
            }}
            
            .fc-daygrid-day {{
                transition: all 0.3s ease;
                border: 1px solid #e8f5e8;
            }}
            
            .fc-daygrid-day:hover {{
                background: rgba(139, 195, 74, 0.1) !important;
            }}
            
            .fc-day-today {{
                background: linear-gradient(135deg, rgba(46, 125, 50, 0.15), rgba(139, 195, 74, 0.15)) !important;
                border: 2px solid #4caf50 !important;
                font-weight: bold;
            }}
            
            .fc-event {{
                background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%) !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 500 !important;
                padding: 2px 6px !important;
                font-size: 0.85rem !important;
                box-shadow: 0 3px 10px rgba(76, 175, 80, 0.3) !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
            }}
            
            .fc-event:hover {{
                transform: scale(1.05) !important;
                box-shadow: 0 5px 20px rgba(76, 175, 80, 0.5) !important;
            }}
            
            .fc-daygrid-day-number {{
                font-weight: 600 !important;
                color: #2e7d32 !important;
            }}
            
            .fc-col-header-cell {{
                background: #f1f8e9 !important;
                color: #1b5e20 !important;
                font-weight: 600 !important;
                border-bottom: 2px solid #81c784 !important;
            }}
        </style>

        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            try {{
                const calendarEl = document.getElementById('calendar');
                if (!calendarEl) {{
                    console.error('캘린더 요소를 찾을 수 없습니다.');
                    return;
                }}

                const calendar = new FullCalendar.Calendar(calendarEl, {{
                    initialView: 'dayGridMonth',
                    locale: 'ko',
                    height: 700,
                    headerToolbar: {{
                        left: 'prev,next today',
                        center: 'title',
                        right: 'dayGridMonth,listWeek'
                    }},
                    buttonText: {{
                        today: '오늘',
                        month: '월별보기',
                        list: '목록보기'
                    }},
                    events: {events_json},
                    eventClick: function(info) {{
                        try {{
                            const content = info.event.extendedProps.description;
                            const calories = info.event.extendedProps.calories || 0;
                            const dateStr = new Date(info.event.start).toLocaleDateString('ko-KR', {{
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                                weekday: 'long'
                            }});
                            
                            if (typeof Swal !== 'undefined') {{
                                Swal.fire({{
                                    title: `<div style="background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%); 
                                                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                                                       font-size: 1.8rem; font-weight: 700; margin-bottom: 10px;">
                                               🍱 ${{dateStr}} 급식
                                             </div>`,
                                    html: `<div style="background: linear-gradient(135deg, #f1f8e9, #e8f5e8); 
                                                      border-radius: 15px; padding: 20px; margin: 15px 0;
                                                      text-align: left; font-size: 1.1rem; line-height: 2; 
                                                      color: #2e7d32; box-shadow: inset 0 2px 10px rgba(46, 125, 50, 0.1);">
                                             ${{content}}
                                             <br><br>
                                             <div style="text-align: center; background: linear-gradient(135deg, #ff9800, #f57c00);
                                                        color: white; padding: 10px; border-radius: 10px; font-weight: 600;">
                                                 🔥 예상 칼로리: ${{calories}}kcal
                                             </div>
                                             <br>
                                             <div style="text-align: center; font-style: italic; 
                                                        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
                                                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                                                        font-size: 1rem; font-weight: 600;">
                                                 🌱 맛있게 드세요! 건강한 하루 되세요! 🌱
                                             </div>
                                           </div>`,
                                    showCloseButton: true,
                                    confirmButtonText: '맛있겠다! 😋',
                                    confirmButtonColor: '#4caf50',
                                    background: 'white',
                                    didOpen: () => {{
                                        if (typeof confetti !== 'undefined') {{
                                            confetti({{
                                                particleCount: 50,
                                                spread: 70,
                                                origin: {{ y: 0.6 }},
                                                colors: ['#4caf50', '#8bc34a', '#81c784', '#a5d6a7']
                                            }});
                                        }}
                                    }}
                                }});
                            }}
                        }} catch (e) {{
                            console.error('이벤트 클릭 오류:', e);
                        }}
                    }},
                    dayCellDidMount: function(info) {{
                        try {{
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);
                            const cellDate = new Date(info.date);
                            cellDate.setHours(0, 0, 0, 0);
                            
                            if(today.getTime() === cellDate.getTime()) {{
                                info.el.classList.add('today-cell');
                            }}
                        }} catch (e) {{
                            console.error('날짜 셀 마운트 오류:', e);
                        }}
                    }}
                }});
                
                calendar.render();
                console.log('캘린더가 성공적으로 렌더링되었습니다.');

                // 폭죽 버튼 이벤트
                const fireworksBtn = document.getElementById('fireworksBtn');
                if (fireworksBtn && typeof confetti !== 'undefined') {{
                    fireworksBtn.onclick = function() {{
                        try {{
                            // 초록 테마 폭죽 효과
                            const duration = 4000;
                            const animationEnd = Date.now() + duration;

                            function randomInRange(min, max) {{
                                return Math.random() * (max - min) + min;
                            }}

                            const interval = setInterval(function() {{
                                const timeLeft = animationEnd - Date.now();
                                if (timeLeft <= 0) {{
                                    clearInterval(interval);
                                    return;
                                }}

                                const particleCount = 50 * (timeLeft / duration);
                                
                                confetti({{
                                    particleCount: particleCount,
                                    startVelocity: 30,
                                    spread: 360,
                                    origin: {{
                                        x: randomInRange(0.1, 0.9),
                                        y: Math.random() - 0.2
                                    }},
                                    colors: ['#4caf50', '#8bc34a', '#81c784', '#a5d6a7', '#2e7d32', '#388e3c']
                                }});
                            }}, 250);

                            // 하트 모양 폭죽 (초록색)
                            setTimeout(() => {{
                                confetti({{
                                    particleCount: 80,
                                    spread: 160,
                                    origin: {{ y: 0.6 }},
                                    colors: ['#4caf50', '#66bb6a', '#81c784'],
                                    shapes: ['square']
                                }});
                            }}, 1000);

                            // 별 모양 폭죽 (초록색)
                            setTimeout(() => {{
                                confetti({{
                                    particleCount: 60,
                                    spread: 100,
                                    origin: {{ y: 0.7 }},
                                    colors: ['#8bc34a', '#9ccc65', '#aed581'],
                                    shapes: ['circle']
                                }});
                            }}, 2000);

                            console.log('폭죽 효과가 실행되었습니다.');
                        }} catch (e) {{
                            console.error('폭죽 효과 오류:', e);
                        }}
                    }};
                }} else {{
                    console.warn('폭죽 버튼이나 confetti 라이브러리를 찾을 수 없습니다.');
                }}

            }} catch (e) {{
                console.error('캘린더 초기화 오류:', e);
            }}
        }});
        </script>
    </body>
    </html>
    """
    
    components.html(calendar_html, height=800, scrolling=False)

def create_beautiful_meal_list(events: List[Dict[str, Any]]):
    """아름다운 급식 목록 생성 (초록 테마, 칼로리 포함)"""
    st.markdown("### 📋 급식 목록")
    
    if not events:
        st.markdown("""
        <div class='info-box'>
            <h3 style='margin: 0 0 10px 0;'>📋 급식 목록</h3>
            <p style='margin: 0;'>표시할 급식 데이터가 없습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 검색 컨테이너
    st.markdown("""
    <div class='search-container'>
        <h3 style='margin: 0 0 15px 0; color: #1b5e20;'>🔍 급식 메뉴 검색</h3>
        <p style='margin: 0; color: #2e7d32;'>찾고 싶은 메뉴나 재료를 검색해보세요!</p>
    </div>
    """, unsafe_allow_html=True)
    
    search_term = st.text_input(
        "", 
        placeholder="🍜 예: 김치찌개, 불고기, 샐러드...", 
        help="메뉴명이나 재료를 입력하세요"
    )
    
    # 데이터 정리
    meal_data = []
    for event in sorted(events, key=lambda x: x['start']):
        date_obj = datetime.datetime.strptime(event['start'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m월 %d일 (%a)')
        weekday = date_obj.strftime('%A')
        
        # 요일별 이모지
        weekday_emoji = {
            'Monday': '🌟', 'Tuesday': '🔥', 'Wednesday': '💎', 
            'Thursday': '🌈', 'Friday': '🎉', 'Saturday': '☀️', 'Sunday': '🌙'
        }
        
        # HTML 태그 제거
        clean_description = re.sub('<.*?>', '', event['extendedProps']['description'])
        clean_description = clean_description.replace('🍽 ', '').replace('<br>', '\n')
        
        calories = event['extendedProps'].get('calories', 0)
        
        meal_data.append({
            "날짜": f"{weekday_emoji.get(weekday, '📅')} {formatted_date}",
            "급식 메뉴": clean_description,
            "메뉴 수": len([m for m in clean_description.split('\n') if m.strip()]),
            "칼로리": calories,
            "원본": event['extendedProps']['description']
        })
    
    # 검색 결과
    if search_term:
        filtered_data = [
            meal for meal in meal_data 
            if search_term.lower() in meal['급식 메뉴'].lower()
        ]
        
        st.markdown(f"""
        <div class='success-box'>
            <h4 style='margin: 0 0 10px 0; color: #1b5e20;'>🎯 검색 결과</h4>
            <p style='margin: 0; color: #2e7d32;'>
                "<strong>{search_term}</strong>"에 대한 검색 결과: <strong>{len(filtered_data)}개</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        display_data = filtered_data
    else:
        display_data = meal_data
    
    # 카드 형태로 표시
    cols = st.columns(2)
    for idx, meal in enumerate(display_data):
        with cols[idx % 2]:
            # 메뉴 미리보기 (처음 3개만)
            menu_preview = meal['급식 메뉴'].split('\n')[:3]
            menu_text = '<br>'.join([f"• {menu.strip()}" for menu in menu_preview if menu.strip()])
            
            if len(meal['급식 메뉴'].split('\n')) > 3:
                menu_text += "<br>• <em>...더보기</em>"
            
            # JavaScript 안전한 문자열 처리
            safe_content = meal['원본'].replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
            
            # 칼로리에 따른 색상 결정
            cal_color = "#4caf50" if meal['칼로리'] <= 600 else "#ff9800" if meal['칼로리'] <= 750 else "#f44336"
            
            st.markdown(f"""
            <div class='meal-card'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                    <h4 style='margin: 0; color: #2e7d32; font-size: 1.2rem; font-weight: 600;'>
                        {meal['날짜']}
                    </h4>
                    <div style='display: flex; gap: 10px; align-items: center;'>
                        <div style='background: {cal_color}; 
                                   color: white; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 500;'>
                            🔥 {meal['칼로리']}kcal
                        </div>
                        <div style='background: linear-gradient(135deg, #4caf50, #388e3c); 
                                   color: white; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 500;'>
                            {meal['메뉴 수']}개 메뉴
                        </div>
                    </div>
                </div>
                <div style='color: #2e7d32; line-height: 1.8; font-size: 0.95rem;'>
                    {menu_text}
                </div>
                <div style='margin-top: 15px; text-align: center;'>
                    <button onclick="showFullMenu{idx}()" 
                            style='background: linear-gradient(135deg, #66bb6a, #4caf50); 
                                   color: white; border: none; padding: 8px 20px; 
                                   border-radius: 20px; cursor: pointer; font-weight: 500;
                                   transition: all 0.3s ease;'
                            onmouseover="this.style.transform='scale(1.05)'"
                            onmouseout="this.style.transform='scale(1)'">
                        전체 메뉴 보기 🍽️
                    </button>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 각 카드마다 개별 스크립트
            components.html(f"""
            <script src='https://cdn.jsdelivr.net/npm/sweetalert2@11'></script>
            <script>
            function showFullMenu{idx}() {{
                if (typeof Swal !== 'undefined') {{
                    Swal.fire({{
                        title: '<div style="color: #2e7d32; font-size: 1.5rem; font-weight: 600;">{meal["날짜"]} 전체 메뉴</div>',
                        html: '<div style="text-align: left; line-height: 2; font-size: 1rem; color: #2e7d32;">{safe_content}</div><br><div style="text-align: center; background: {cal_color}; color: white; padding: 10px; border-radius: 10px; font-weight: 600;">🔥 예상 칼로리: {meal["칼로리"]}kcal</div>',
                        confirmButtonText: '맛있겠어요! 😋',
                        confirmButtonColor: '#4caf50',
                        showCloseButton: true,
                        width: '600px',
                        background: '#f9f9f9'
                    }});
                }} else {{
                    alert('전체 메뉴:\\n{meal["급식 메뉴"]}\\n\\n칼로리: {meal["칼로리"]}kcal');
                }}
            }}
            </script>
            """, height=0)
    
    # 전체 데이터프레임 (숨김 가능)
    with st.expander("📊 전체 데이터 테이블로 보기"):
        df = pd.DataFrame([{
            "날짜": meal["날짜"], 
            "급식 메뉴": meal["급식 메뉴"],
            "칼로리": f"{meal['칼로리']}kcal"
        } for meal in display_data])
        st.dataframe(df, use_container_width=True, height=400)

def create_mini_games(events: List[Dict[str, Any]]):
    """미니게임 탭 생성"""
    st.markdown("### 🎮 미니게임 센터")
    st.markdown("""
    <div style='text-align: center; background: linear-gradient(135deg, #ff9800, #f57c00); 
               color: white; padding: 20px; border-radius: 20px; margin: 20px 0;'>
        <h3 style='margin: 0 0 10px 0;'>🎯 점심시간이 심심할 때 플레이해보세요!</h3>
        <p style='margin: 0; font-size: 1.1rem;'>급식과 관련된 재미있는 게임들을 준비했어요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 게임 선택
    game_col1, game_col2 = st.columns(2)
    
    with game_col1:
        if st.button("🍱 급식 메뉴 맞추기", key="menu_quiz", help="오늘의 급식 메뉴를 맞춰보세요!"):
            st.session_state.selected_game = "menu_quiz"
        
        if st.button("🎯 칼로리 추정 게임", key="calorie_game", help="급식의 칼로리를 추정해보세요!"):
            st.session_state.selected_game = "calorie_game"
    
    with game_col2:
        if st.button("🃏 급식 카드 매칭", key="card_matching", help="같은 메뉴 카드를 찾아보세요!"):
            st.session_state.selected_game = "card_matching"
        
        if st.button("🎲 행운의 메뉴 뽑기", key="lucky_menu", help="랜덤으로 메뉴를 추천받아보세요!"):
            st.session_state.selected_game = "lucky_menu"
    
    # 선택된 게임 실행
    if hasattr(st.session_state, 'selected_game'):
        st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
        
        if st.session_state.selected_game == "menu_quiz":
            play_menu_quiz(events)
        elif st.session_state.selected_game == "calorie_game":
            play_calorie_game(events)
        elif st.session_state.selected_game == "card_matching":
            play_card_matching(events)
        elif st.session_state.selected_game == "lucky_menu":
            play_lucky_menu(events)

def play_menu_quiz(events: List[Dict[str, Any]]):
    """급식 메뉴 맞추기 게임"""
    st.markdown("### 🍱 급식 메뉴 맞추기")
    
    if not events:
        st.error("급식 데이터가 없습니다.")
        return
    
    # 게임 초기화
    if 'quiz_score' not in st.session_state:
        st.session_state.quiz_score = 0
        st.session_state.quiz_count = 0
        st.session_state.current_quiz = None
    
    # 새 문제 생성
    if st.button("새 문제 출제!", key="new_quiz"):
        random_event = random.choice(events)
        clean_menu = re.sub('<.*?>', '', random_event['extendedProps']['description'])
        menu_items = [item.strip().replace('🍽 ', '') for item in clean_menu.split('\n') if item.strip()]
        
        if len(menu_items) >= 3:
            correct_answer = random.choice(menu_items)
            wrong_answers = [item for item in menu_items if item != correct_answer]
            
            # 다른 날짜의 메뉴에서 틀린 답 가져오기
            other_events = [e for e in events if e != random_event]
            for other_event in random.sample(other_events, min(3, len(other_events))):
                other_menu = re.sub('<.*?>', '', other_event['extendedProps']['description'])
                other_items = [item.strip().replace('🍽 ', '') for item in other_menu.split('\n') if item.strip()]
                wrong_answers.extend(other_items[:2])
            
            # 선택지 생성 (정답 1개 + 오답 3개)
            choices = [correct_answer] + random.sample(wrong_answers, min(3, len(wrong_answers)))
            random.shuffle(choices)
            
            date_obj = datetime.datetime.strptime(random_event['start'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m월 %d일')
            
            st.session_state.current_quiz = {
                'date': formatted_date,
                'menu': clean_menu,
                'correct_answer': correct_answer,
                'choices': choices,
                'calories': random_event['extendedProps'].get('calories', 0)
            }
    
    # 현재 퀴즈 표시
    if st.session_state.current_quiz:
        quiz = st.session_state.current_quiz
        
        st.markdown(f"""
        <div class='game-card'>
            <h4 style='color: #e65100; text-align: center; margin-bottom: 20px;'>
                📅 {quiz['date']} 급식 메뉴 중에서...
            </h4>
            <div style='background: white; padding: 15px; border-radius: 10px; margin: 15px 0;'>
                <p style='font-size: 1.1rem; text-align: center; color: #2e7d32;'>
                    다음 중 <strong>실제로 나온 메뉴</strong>는 무엇일까요?
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 선택지
        user_answer = st.radio(
            "정답을 선택하세요:",
            quiz['choices'],
            key="quiz_answer"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("정답 확인!", key="check_answer"):
                st.session_state.quiz_count += 1
                if user_answer == quiz['correct_answer']:
                    st.session_state.quiz_score += 1
                    st.success(f"🎉 정답입니다! '{quiz['correct_answer']}'가 맞아요!")
                    st.balloons()
                else:
                    st.error(f"❌ 틀렸어요. 정답은 '{quiz['correct_answer']}'입니다.")
                
                # 전체 메뉴 보여주기
                st.markdown(f"""
                <div class='success-box'>
                    <h4>📋 {quiz['date']} 전체 메뉴</h4>
                    <p style='line-height: 2;'>{quiz['menu'].replace(chr(10), '<br>')}</p>
                    <p style='text-align: center; font-weight: bold; color: #ff6600;'>
                        🔥 칼로리: {quiz['calories']}kcal
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if st.button("힌트 보기", key="show_hint"):
                st.info(f"💡 힌트: 칼로리는 {quiz['calories']}kcal 입니다!")
    
    # 점수 표시
    if st.session_state.quiz_count > 0:
        accuracy = (st.session_state.quiz_score / st.session_state.quiz_count) * 100
        st.markdown(f"""
        <div class='stat-card' style='margin: 20px auto; max-width: 300px;'>
            <h4 style='margin: 0 0 10px 0;'>🏆 게임 성과</h4>
            <p style='margin: 5px 0;'>정답: {st.session_state.quiz_score}개</p>
            <p style='margin: 5px 0;'>총 문제: {st.session_state.quiz_count}개</p>
            <p style='margin: 5px 0;'>정답률: {accuracy:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

def play_calorie_game(events: List[Dict[str, Any]]):
    """칼로리 추정 게임"""
    st.markdown("### 🎯 칼로리 추정 게임")
    
    if not events:
        st.error("급식 데이터가 없습니다.")
        return
    
    # 게임 초기화
    if 'calorie_score' not in st.session_state:
        st.session_state.calorie_score = 0
        st.session_state.calorie_count = 0
        st.session_state.current_calorie_quiz = None
    
    # 새 문제 생성
    if st.button("새 메뉴 도전!", key="new_calorie_quiz"):
        random_event = random.choice(events)
        clean_menu = re.sub('<.*?>', '', random_event['extendedProps']['description'])
        date_obj = datetime.datetime.strptime(random_event['start'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%m월 %d일')
        
        st.session_state.current_calorie_quiz = {
            'date': formatted_date,
            'menu': clean_menu,
            'actual_calories': random_event['extendedProps'].get('calories', 0)
        }
    
    # 현재 퀴즈 표시
    if st.session_state.current_calorie_quiz:
        quiz = st.session_state.current_calorie_quiz
        
        st.markdown(f"""
        <div class='game-card'>
            <h4 style='color: #e65100; text-align: center; margin-bottom: 20px;'>
                📅 {quiz['date']} 급식의 칼로리는?
            </h4>
            <div style='background: white; padding: 15px; border-radius: 10px; margin: 15px 0;'>
                <div style='color: #2e7d32; line-height: 2;'>
                    {quiz['menu'].replace(chr(10), '<br>')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 칼로리 추정
        estimated_calories = st.slider(
            "이 급식의 칼로리는 몇 kcal일까요?",
            min_value=300,
            max_value=1000,
            value=600,
            step=10,
            key="calorie_estimate"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("추정 완료!", key="check_calorie"):
                st.session_state.calorie_count += 1
                actual = quiz['actual_calories']
                difference = abs(estimated_calories - actual)
                accuracy = max(0, 100 - (difference / actual * 100))
                
                if difference <= 50:
                    st.session_state.calorie_score += 1
                    st.success(f"🎯 대박! 실제 칼로리는 {actual}kcal입니다! (차이: {difference}kcal)")
                    st.balloons()
                elif difference <= 100:
                    st.warning(f"👍 좋아요! 실제 칼로리는 {actual}kcal입니다! (차이: {difference}kcal)")
                else:
                    st.error(f"😅 아쉬워요! 실제 칼로리는 {actual}kcal입니다! (차이: {difference}kcal)")
                
                st.markdown(f"""
                <div class='info-box'>
                    <p style='margin: 0; text-align: center;'>
                        🎯 정확도: {accuracy:.1f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if st.button("칼로리 힌트", key="calorie_hint"):
                actual = quiz['actual_calories']
                if actual < 500:
                    st.info("💡 힌트: 가벼운 식사 수준입니다!")
                elif actual < 700:
                    st.info("💡 힌트: 적당한 식사 수준입니다!")
                else:
                    st.info("💡 힌트: 든든한 식사 수준입니다!")
    
    # 점수 표시
    if st.session_state.calorie_count > 0:
        accuracy = (st.session_state.calorie_score / st.session_state.calorie_count) * 100
        st.markdown(f"""
        <div class='stat-card' style='margin: 20px auto; max-width: 300px;'>
            <h4 style='margin: 0 0 10px 0;'>🔥 칼로리 마스터</h4>
            <p style='margin: 5px 0;'>정확한 추정: {st.session_state.calorie_score}개</p>
            <p style='margin: 5px 0;'>총 추정: {st.session_state.calorie_count}개</p>
            <p style='margin: 5px 0;'>성공률: {accuracy:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

def play_card_matching(events: List[Dict[str, Any]]):
    """급식 카드 매칭 게임"""
    st.markdown("### 🃏 급식 카드 매칭")
    
    if len(events) < 4:
        st.error("카드 게임을 위한 충분한 데이터가 없습니다.")
        return
    
    # 게임 초기화
    if 'cards' not in st.session_state:
        # 4쌍의 카드 생성
        selected_events = random.sample(events, 4)
        cards = []
        for i, event in enumerate(selected_events):
            clean_menu = re.sub('<.*?>', '', event['extendedProps']['description'])
            menu_items = [item.strip().replace('🍽 ', '') for item in clean_menu.split('\n') if item.strip()]
            main_menu = menu_items[0] if menu_items else "급식"
            
            # 같은 메뉴 2장씩
            cards.extend([{'id': i, 'menu': main_menu, 'flipped': False, 'matched': False}] * 2)
        
        random.shuffle(cards)
        st.session_state.cards = cards
        st.session_state.flipped_cards = []
        st.session_state.matches = 0
        st.session_state.moves = 0
    
    # 게임 리셋
    if st.button("새 게임 시작!", key="reset_cards"):
        del st.session_state.cards
        st.rerun()
    
    # 카드 표시
    st.markdown("### 같은 메뉴 카드 두 장을 찾아보세요!")
    
    cols = st.columns(4)
    for i, card in enumerate(st.session_state.cards):
        with cols[i % 4]:
            if i % 4 == 0 and i > 0:
                st.markdown("<br>", unsafe_allow_html=True)
            
            # 카드 버튼
            if card['matched']:
                st.success(f"✅ {card['menu']}")
            elif card['flipped'] or i in st.session_state.flipped_cards:
                st.info(f"🍽️ {card['menu']}")
            else:
                if st.button("❓", key=f"card_{i}", help="클릭해서 카드를 뒤집어보세요"):
                    if len(st.session_state.flipped_cards) < 2 and not card['flipped']:
                        st.session_state.flipped_cards.append(i)
                        st.session_state.moves += 1
                        
                        # 두 장이 뒤집어졌을 때 매칭 확인
                        if len(st.session_state.flipped_cards) == 2:
                            card1_idx, card2_idx = st.session_state.flipped_cards
                            card1 = st.session_state.cards[card1_idx]
                            card2 = st.session_state.cards[card2_idx]
                            
                            if card1['id'] == card2['id']:  # 같은 메뉴
                                st.session_state.cards[card1_idx]['matched'] = True
                                st.session_state.cards[card2_idx]['matched'] = True
                                st.session_state.matches += 1
                                st.success("🎉 매칭 성공!")
                            else:
                                st.error("💭 다시 시도해보세요!")
                            
                            st.session_state.flipped_cards = []
                        
                        st.rerun()
    
    # 게임 상태 표시
    st.markdown(f"""
    <div class='success-box'>
        <p style='margin: 0; text-align: center;'>
            🎯 매칭: {st.session_state.matches}/4 | 🔄 시도: {st.session_state.moves}번
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 게임 완료
    if st.session_state.matches == 4:
        st.balloons()
        st.success(f"🏆 축하합니다! {st.session_state.moves}번 만에 모든 카드를 매칭했습니다!")

def play_lucky_menu(events: List[Dict[str, Any]]):
    """행운의 메뉴 뽑기 게임"""
    st.markdown("### 🎲 행운의 메뉴 뽑기")
    
    if not events:
        st.error("급식 데이터가 없습니다.")
        return
    
    st.markdown("""
    <div class='game-card'>
        <h4 style='color: #e65100; text-align: center; margin-bottom: 20px;'>
            🔮 오늘의 운세를 확인해보세요!
        </h4>
        <p style='text-align: center; color: #2e7d32; font-size: 1.1rem;'>
            랜덤으로 급식 메뉴를 뽑아서 운세를 알아보는 재미있는 게임입니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🍀 행운의 메뉴", key="lucky_draw"):
            random_event = random.choice(events)
            clean_menu = re.sub('<.*?>', '', random_event['extendedProps']['description'])
            menu_items = [item.strip().replace('🍽 ', '') for item in clean_menu.split('\n') if item.strip()]
            lucky_menu = random.choice(menu_items) if menu_items else "특별한 메뉴"
            
            date_obj = datetime.datetime.strptime(random_event['start'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m월 %d일')
            calories = random_event['extendedProps'].get('calories', 0)
            
            # 운세 메시지 생성
            fortunes = [
                "오늘은 새로운 도전을 해보는 것이 좋겠어요! 🌟",
                "친구들과 함께 하는 시간이 특별한 행운을 가져다 줄 거예요! 👫",
                "공부에 집중하면 좋은 결과가 있을 것 같아요! 📚",
                "가족과의 시간을 소중히 하세요! 💕",
                "오늘 하루 웃음이 많은 하루가 될 것 같아요! 😊",
                "새로운 취미를 시작해보는 것은 어떨까요? 🎨",
                "건강에 신경 쓰는 하루가 되길 바라요! 💪"
            ]
            
            fortune = random.choice(fortunes)
            
            st.markdown(f"""
            <div class='success-box'>
                <h3 style='color: #1b5e20; text-align: center; margin-bottom: 15px;'>
                    🎉 행운의 메뉴가 결정되었습니다!
                </h3>
                <div style='background: white; padding: 20px; border-radius: 15px; text-align: center;'>
                    <h2 style='color: #2e7d32; margin: 10px 0;'>🍽️ {lucky_menu}</h2>
                    <p style='color: #666; margin: 5px 0;'>📅 {formatted_date} 급식</p>
                    <p style='color: #ff6600; margin: 5px 0; font-weight: bold;'>🔥 {calories}kcal</p>
                </div>
                <div style='margin-top: 15px; padding: 15px; background: linear-gradient(135deg, #fff3e0, #ffe0b2); border-radius: 10px;'>
                    <h4 style='color: #e65100; margin: 0 0 10px 0; text-align: center;'>🔮 오늘의 운세</h4>
                    <p style='color: #2e7d32; margin: 0; text-align: center; font-size: 1.1rem;'>{fortune}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🎯 칼로리 추천", key="calorie_recommend"):
            # 사용자의 목표 칼로리 입력받기
            target_calories = st.slider("목표 칼로리를 설정하세요", 400, 800, 650, step=50)
            
            # 목표 칼로리와 가장 가까운 메뉴 찾기
            best_match = None
            min_diff = float('inf')
            
            for event in events:
                event_calories = event['extendedProps'].get('calories', 0)
                diff = abs(event_calories - target_calories)
                if diff < min_diff:
                    min_diff = diff
                    best_match = event
            
            if best_match:
                clean_menu = re.sub('<.*?>', '', best_match['extendedProps']['description'])
                date_obj = datetime.datetime.strptime(best_match['start'], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m월 %d일')
                actual_calories = best_match['extendedProps'].get('calories', 0)
                
                st.markdown(f"""
                <div class='info-box'>
                    <h3 style='color: #e65100; text-align: center; margin-bottom: 15px;'>
                        🎯 칼로리 맞춤 추천!
                    </h3>
                    <div style='background: white; padding: 15px; border-radius: 10px;'>
                        <p style='color: #2e7d32; text-align: center; margin: 5px 0;'>
                            📅 {formatted_date} 급식
                        </p>
                        <p style='color: #ff6600; text-align: center; font-weight: bold; margin: 10px 0;'>
                            🔥 {actual_calories}kcal (목표: {target_calories}kcal)
                        </p>
                        <div style='color: #2e7d32; line-height: 2; margin-top: 15px;'>
                            {clean_menu.replace(chr(10), '<br>')}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with col3:
        if st.button("🌟 이번 주 베스트", key="weekly_best"):
            # 이번 주 날짜 계산
            today = datetime.datetime.now(KST)
            week_start = today - datetime.timedelta(days=today.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            
            week_events = [
                event for event in events 
                if week_start.strftime('%Y-%m-%d') <= event['start'] <= week_end.strftime('%Y-%m-%d')
            ]
            
            if week_events:
                # 칼로리가 가장 적당한 메뉴 (600-700kcal) 찾기
                best_events = [
                    event for event in week_events 
                    if 600 <= event['extendedProps'].get('calories', 0) <= 700
                ]
                
                if not best_events:
                    best_events = week_events
                
                best_event = random.choice(best_events)
                clean_menu = re.sub('<.*?>', '', best_event['extendedProps']['description'])
                date_obj = datetime.datetime.strptime(best_event['start'], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m월 %d일')
                calories = best_event['extendedProps'].get('calories', 0)
                
                st.markdown(f"""
                <div class='success-box'>
                    <h3 style='color: #1b5e20; text-align: center; margin-bottom: 15px;'>
                        ⭐ 이번 주 베스트 급식!
                    </h3>
                    <div style='background: white; padding: 15px; border-radius: 10px;'>
                        <p style='color: #2e7d32; text-align: center; margin: 5px 0;'>
                            📅 {formatted_date} 급식
                        </p>
                        <p style='color: #ff6600; text-align: center; font-weight: bold; margin: 10px 0;'>
                            🔥 {calories}kcal
                        </p>
                        <div style='color: #2e7d32; line-height: 2; margin-top: 15px;'>
                            {clean_menu.replace(chr(10), '<br>')}
                        </div>
                    </div>
                    <p style='color: #4caf50; text-align: center; margin: 15px 0 0 0; font-weight: 600;'>
                        🌟 영양과 맛의 완벽한 균형! 🌟
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("이번 주 급식 데이터가 없습니다.")

def create_school_info():
    """학교 정보 탭 생성 (초록 테마)"""
    st.markdown("### ℹ️ 학교 및 애플리케이션 정보")
    
    # 학교 정보 카드
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class='meal-card'>
            <h4 style='color: #2e7d32; margin-bottom: 20px; font-size: 1.3rem;'>🏫 학교 정보</h4>
            <div style='line-height: 2; color: #1b5e20;'>
                <p><strong>🏛️ 학교명:</strong> 상암고등학교</p>
                <p><strong>📍 위치:</strong> 서울특별시</p>
                <p><strong>🏢 교육청:</strong> 서울특별시교육청</p>
                <p><strong>📞 급식 문의:</strong> 학교 행정실</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class='meal-card'>
            <h4 style='color: #388e3c; margin-bottom: 20px; font-size: 1.3rem;'>🔄 데이터 정보</h4>
            <div style='line-height: 2; color: #1b5e20;'>
                <p><strong>📊 데이터 출처:</strong> 나이스 교육정보 개방포털</p>
                <p><strong>⏰ 업데이트 주기:</strong> 1시간마다 자동 갱신</p>
                <p><strong>📅 제공 범위:</strong> 지난 30일 ~ 향후 31일</p>
                <p><strong>🔒 데이터 안정성:</strong> 캐시 시스템 적용</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='meal-card'>
            <h4 style='color: #d84315; margin-bottom: 20px; font-size: 1.3rem;'>🏥 알레르기 정보</h4>
            <div style='line-height: 1.8; color: #1b5e20; font-size: 0.9rem;'>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px;'>
                    <div>1. 난류(계란)</div><div>2. 우유</div>
                    <div>3. 메밀</div><div>4. 땅콩</div>
                    <div>5. 대두</div><div>6. 밀</div>
                    <div>7. 고등어</div><div>8. 게</div>
                    <div>9. 새우</div><div>10. 돼지고기</div>
                    <div>11. 복숭아</div><div>12. 토마토</div>
                    <div>13. 아황산류</div><div>14. 호두</div>
                    <div>15. 닭고기</div><div>16. 쇠고기</div>
                    <div>17. 오징어</div><div>18. 조개류</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class='meal-card'>
            <h4 style='color: #2e7d32; margin-bottom: 20px; font-size: 1.3rem;'>💡 사용 가이드</h4>
            <div style='line-height: 2; color: #1b5e20;'>
                <p><strong>📅 캘린더:</strong> 날짜 클릭으로 상세 메뉴 확인</p>
                <p><strong>🔍 검색:</strong> 원하는 메뉴나 재료 검색</p>
                <p><strong>🎮 게임:</strong> 재미있는 급식 미니게임</p>
                <p><strong>🎆 폭죽:</strong> 우하단 버튼으로 재미있는 효과</p>
                <p><strong>📱 반응형:</strong> 모바일, 태블릿 최적화</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 새로운 기능 소개
    st.markdown("""
    <div style='background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c8 100%); 
               border-radius: 20px; padding: 30px; margin: 30px 0;'>
        <h3 style='color: #1b5e20; text-align: center; margin-bottom: 20px; font-size: 1.5rem;'>
            🆕 새로운 기능들
        </h3>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;'>
            <div style='background: white; padding: 20px; border-radius: 15px; text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 10px;'>🔥</div>
                <h4 style='color: #2e7d32; margin: 10px 0;'>칼로리 정보</h4>
                <p style='color: #666; margin: 0; font-size: 0.9rem;'>
                    각 급식의 예상 칼로리를 확인할 수 있어요
                </p>
            </div>
            <div style='background: white; padding: 20px; border-radius: 15px; text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 10px;'>🎮</div>
                <h4 style='color: #2e7d32; margin: 10px 0;'>미니게임</h4>
                <p style='color: #666; margin: 0; font-size: 0.9rem;'>
                    급식 관련 재미있는 게임을 즐겨보세요
                </p>
            </div>
            <div style='background: white; padding: 20px; border-radius: 15px; text-align: center;'>
                <div style='font-size: 2rem; margin-bottom: 10px;'>📊</div>
                <h4 style='color: #2e7d32; margin: 10px 0;'>통계 정보</h4>
                <p style='color: #666; margin: 0; font-size: 0.9rem;'>
                    평균 칼로리 등 다양한 통계를 확인해보세요
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 피드백 섹션
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%); 
               border-radius: 20px; padding: 30px; margin: 30px 0; text-align: center;'>
        <h3 style='color: white; margin-bottom: 15px; font-size: 1.5rem;'>💌 소중한 의견을 들려주세요!</h3>
        <p style='color: rgba(255,255,255,0.9); font-size: 1.1rem; margin-bottom: 20px;'>
            더 나은 급식 캘린더를 만들어가고 싶습니다
        </p>
        <div style='display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;'>
            <div style='background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 25px;'>
                <span style='color: white; font-weight: 500;'>📧 개선사항 제안</span>
            </div>
            <div style='background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 25px;'>
                <span style='color: white; font-weight: 500;'>🐛 버그 신고</span>
            </div>
            <div style='background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 25px;'>
                <span style='color: white; font-weight: 500;'>⭐ 기능 요청</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 마지막 업데이트 정보
    st.markdown(f"""
    <div style='text-align: center; color: #1b5e20; font-size: 0.9rem; 
               margin: 30px 0; padding: 20px; background: #f1f8e9; border-radius: 15px;
               border: 1px solid #c8e6c8;'>
        <p style='margin: 0;'>
            🔄 마지막 데이터 갱신: <strong>{TODAY.strftime("%Y년 %m월 %d일 %H:%M")}</strong>
        </p>
        <p style='margin: 10px 0 0 0; font-style: italic;'>
            🌱 매일매일 건강하고 맛있는 급식, 감사하게 먹어요! 🍱💚
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()