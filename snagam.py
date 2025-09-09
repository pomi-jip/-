import run
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
                
                events.append({
                    "title": "🍴 급식",
                    "start": formatted_date,
                    "extendedProps": {
                        "description": meals_text,
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
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🍽️</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{len(events) * 4}</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>예상 메뉴 수</div>
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
                <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🔄</div>
                <div style='font-size: 1.2rem; font-weight: bold;'>1시간</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>업데이트 주기</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin: 0 0 10px 0; color: #1b5e20;'>🎉 데이터 로딩 완료!</h3>
            <p style='margin: 0; color: #2e7d32; font-size: 1.1rem;'>
                총 <strong>{len(events)}일</strong>의 맛있는 급식 정보를 성공적으로 불러왔습니다!
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
    tab1, tab2, tab3 = st.tabs(["📅 급식 캘린더", "📋 급식 목록", "ℹ️ 학교 정보"])
    
    with tab1:
        create_green_calendar(events)
    
    with tab2:
        create_beautiful_meal_list(events)
    
    with tab3:
        create_school_info()

def create_green_calendar(events: List[Dict[str, Any]]):
    """초록 테마 캘린더 UI 생성"""
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
    """아름다운 급식 목록 생성 (초록 테마)"""
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
        
        meal_data.append({
            "날짜": f"{weekday_emoji.get(weekday, '📅')} {formatted_date}",
            "급식 메뉴": clean_description,
            "메뉴 수": len([m for m in clean_description.split('\n') if m.strip()]),
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
            
            st.markdown(f"""
            <div class='meal-card'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                    <h4 style='margin: 0; color: #2e7d32; font-size: 1.2rem; font-weight: 600;'>
                        {meal['날짜']}
                    </h4>
                    <div style='background: linear-gradient(135deg, #4caf50, #388e3c); 
                               color: white; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: 500;'>
                        {meal['메뉴 수']}개 메뉴
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
                        html: '<div style="text-align: left; line-height: 2; font-size: 1rem; color: #2e7d32;">{safe_content}</div>',
                        confirmButtonText: '맛있겠어요! 😋',
                        confirmButtonColor: '#4caf50',
                        showCloseButton: true,
                        width: '600px',
                        background: '#f9f9f9'
                    }});
                }} else {{
                    alert('전체 메뉴:\\n{meal["급식 메뉴"]}');
                }}
            }}
            </script>
            """, height=0)
    
    # 전체 데이터프레임 (숨김 가능)
    with st.expander("📊 전체 데이터 테이블로 보기"):
        df = pd.DataFrame([{
            "날짜": meal["날짜"], 
            "급식 메뉴": meal["급식 메뉴"]
        } for meal in display_data])
        st.dataframe(df, use_container_width=True, height=400)

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
                <p><strong>🎆 폭죽:</strong> 우하단 버튼으로 재미있는 효과</p>
                <p><strong>📱 반응형:</strong> 모바일, 태블릿 최적화</p>
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