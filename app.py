import streamlit as st
import os
import gspread
from google.oauth2.service_account import Credentials
import re
import datetime
today = datetime.date.today() # 오늘 날짜 정의

# 세션 상태 초기화
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'student_info'
if 'student_data' not in st.session_state:
    st.session_state.student_data = None
if 'service_data' not in st.session_state:
    st.session_state.service_data = []

# 페이지 전환 함수
def navigate_to(page_name):
    st.session_state.current_page = page_name

def authenticate_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials_path = 'C:/Users/user/Desktop/성적표신청app/credentials.json' # 실제 경로
    creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key('12o5QjTkjDfMWnGb-BXm9RRWmFN7FQqquucOnZU5BqnY')  # 스프레드시트 ID 입력
    return spreadsheet.sheet1

# 데이터 저장 함수
def save_to_google_sheet(student_data, service_data):
    try:
        sheet = authenticate_google_sheets()
        
        # 현재 시간 (Timestamp)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 기본 학생 정보
        base_row = [
            timestamp,
            student_data['name'],
            student_data['dob'],
            student_data['email'],
            student_data['student_id'],
        ]
        
        rows = []  # 스프레드시트에 추가할 행 데이터
        
        # 이메일 서비스 데이터 저장
        email_data = service_data.get('email', {})
        for recipient in email_data.get('recipients', []):
            row = base_row + [
                "Email",  # Service Type
                recipient.get('name', ''),
                recipient.get('email', ''),
                recipient.get('cc_email', ''),
                '', '', '',  # Postal 관련 데이터 없음
                1,  # 이메일은 문서 1장 고정
                2000  # 이메일 수수료
            ]
            rows.append(row)
        
        # 국내 우편 서비스 데이터 저장
        domestic_data = service_data.get('domestic', [])
        for domestic in domestic_data:
            row = base_row + [
                "Domestic Post",  # Service Type
                '', '', '',  # Recipient Email 관련 데이터 없음
                domestic.get('name', ''),
                domestic.get('address', ''),
                domestic.get('contact', ''),
                domestic.get('documents', 1),
                4000  # 국내 우편 기본 수수료
            ]
            rows.append(row)
        
        # 해외 우편 서비스 데이터 저장
        international_data = service_data.get('international_post', [])
        for international in international_data:
            row = base_row + [
                "International Post",  # Service Type
                '', '', '',  # Recipient Email 관련 데이터 없음
                international.get('name', ''),
                international.get('address', ''),
                international.get('contact', ''),
                international.get('documents', 1),
                50000  # 해외 우편 기본 수수료
            ]
            rows.append(row)
        
        # 데이터 추가
        sheet.append_rows(rows, value_input_option="RAW")
        st.success("데이터가 성공적으로 저장되었습니다!")
    except Exception as e:
        st.error(f"Google Sheets 저장 중 오류 발생: {e}")

# 페이지 1: 학생 정보 입력
def student_info_page():
    st.title("학생 정보 입력")

    # 기존 세션 상태 값 불러오기 (없으면 기본값 설정)
    name = st.text_input("이름", value=st.session_state.get("name", ""))
    dob = st.date_input("생년월일", 
                        value=st.session_state.get("dob", today), 
                        min_value=datetime.date(1960, 1, 1), 
                        max_value=today)
    email = st.text_input("이메일", value=st.session_state.get("email", ""))
    student_id = st.text_input("학번", value=st.session_state.get("student_id", ""), max_chars=10)
    # 학번 유효성 검사
    if student_id and not re.match(r'^\d{10}$', student_id):
       st.error("학번은 10자리 숫자로 입력해 주세요.")

    st.write("""
    개인정보 제공 및 활용에 동의하시겠습니까?
    - 입력하신 개인정보는 본 서비스 제공 목적으로만 사용됩니다.
    - 동의하지 않을 경우, 서비스 이용이 제한됩니다.
    """)
    agree = st.checkbox("동의합니다.", key="privacy_agreement", value=st.session_state.get("agree", False))

    # 버튼 처리
    if st.button("다음"):
        if not all([name, dob, email, student_id, agree]):
            st.error("모든 필드를 입력하고 동의해야 합니다.")
        else:
            # 학생 정보를 세션 상태에 저장
            st.session_state["student_data"] = {
                "name": name,
                "dob": dob,
                "email": email,
                "student_id": student_id,
                "agree": agree
            }
            st.session_state["page"] = "service_selection"  # 다음 페이지로 이동

# 페이지 2: 서비스 유형 선택
def service_selection_page():
    st.title("서비스 유형 선택")

    # 세션에서 학생 데이터 불러오기
    student_data = st.session_state.get('student_data', None)
    if not student_data:
        st.error("학생 정보가 없습니다. 이전 화면으로 돌아가세요.")
        return

    # 초기값 설정
    email_service = st.session_state.get("email_service", False)
    domestic = st.session_state.get("postal_service_domestic", False)
    international = st.session_state.get("postal_service_international", False)

    # 서비스 유형 선택 (체크박스)
    email_service_checkbox = st.checkbox("이메일", value=email_service, key="email_service_checkbox")
    domestic_checkbox = st.checkbox("국내 우편", value=domestic, key="domestic_service_checkbox")
    international_checkbox = st.checkbox("해외 우편", value=international, key="international_service_checkbox")

    # 서비스 선택 안 했을 때 메시지
    if not (email_service_checkbox or domestic_checkbox or international_checkbox):
        st.warning("서비스 유형을 선택해주세요.")
    
    service_info = {}
    total_fee = 0  # 수수료 초기화

    # 이메일 서비스 세부 입력
    if email_service_checkbox:
        with st.expander("이메일 발송 내역"):
            email_count = st.number_input("이메일 발송 건수", min_value=1, value=st.session_state.get("email_count", 1), key="email_count")
            # 이메일 서류 수는 항상 1장으로 고정
            num_documents = 1

            recipients = []
            for i in range(email_count):
                email_recipient = st.text_input(f"이메일 {i+1} 수신인 이메일", key=f"email_recipient_{i+1}")
                cc_email = st.text_input(f"이메일 {i+1} 참조 이메일 (선택)", key=f"cc_email_{i+1}")
                recipients.append({'email': email_recipient, 'cc_email': cc_email})

            service_info['email'] = {'recipients': recipients}  # 이메일에 서류 수는 필요 없으므로 제외
            total_fee += email_count * 2000  # 추가 서류 수수료는 항상 0

    # 국내 우편 서비스 세부 입력
    if domestic_checkbox:
        with st.expander("국내 우편 발송 내역"):
            domestic_count = st.number_input("국내 우편 발송 건수", min_value=1, value=st.session_state.get("domestic_count", 1), key="domestic_count")
            domestic_recipients = []
            for i in range(domestic_count):
                name = st.text_input(f"우편 {i+1} 수신인 이름", key=f"domestic_name_{i+1}")
                address = st.text_input(f"우편 {i+1} 수신인 주소", key=f"domestic_address_{i+1}")
                contact = st.text_input(f"우편 {i+1} 수신인 연락처", key=f"domestic_contact_{i+1}")
                documents = st.number_input(f"우편 {i+1} 서류 수", min_value=1, step=1, key=f"domestic_docs_{i+1}")
                domestic_recipients.append({'name': name, 'address': address, 'contact': contact, 'documents': documents})
            service_info['domestic'] = domestic_recipients
            total_fee += domestic_count * 4000 + (documents - 1) * 1000

    # 해외 우편 서비스 세부 입력
    if international_checkbox:
        with st.expander("해외 우편 발송 내역"):
            international_count = st.number_input("해외 우편 발송 건수", min_value=1, value=st.session_state.get("international_count", 1), key="international_count")
            international_recipients = []
            for i in range(international_count):
                name = st.text_input(f"해외 우편 {i+1} 수신인 이름", key=f"international_name_{i+1}")
                address = st.text_input(f"해외 우편 {i+1} 수신인 주소", key=f"international_address_{i+1}")
                contact = st.text_input(f"해외 우편 {i+1} 수신인 연락처", key=f"international_contact_{i+1}")
                documents = st.number_input(f"해외 우편 {i+1} 서류 수", min_value=1, step=1, key=f"international_docs_{i+1}")
                international_recipients.append({'name': name, 'address': address, 'contact': contact, 'documents': documents})
            service_info['international_post'] = international_recipients
            total_fee += international_count * 50000 + (documents - 1) * 1000

    # 서비스 선택 상태 저장 (위젯 key에 따라)
    if email_service_checkbox != email_service:
        st.session_state["email_service"] = email_service_checkbox
    if domestic_checkbox != domestic:
        st.session_state["postal_service_domestic"] = domestic_checkbox
    if international_checkbox != international:
        st.session_state["postal_service_international"] = international_checkbox

    # 버튼 처리
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("이전", key="previous_button_service_selection_2"):
            st.session_state["page"] = "student_info"
    with col2:
        if st.button("다음", key="next_button_service_selection"):
            if not (email_service_checkbox or domestic_checkbox or international_checkbox):
                st.warning("서비스 유형을 선택해주세요.")
            elif email_service_checkbox and not email_count:
                st.warning("이메일 발송 건수를 입력해야 합니다.")
            elif domestic_checkbox and not domestic_count:
                st.warning("국내 우편 발송 건수를 입력해야 합니다.")
            elif international_checkbox and not international_count:
                st.warning("해외 우편 발송 건수를 입력해야 합니다.")
            else:
                # 세션에 선택된 정보 저장
                st.session_state["email_service"] = email_service_checkbox
                st.session_state["domestic"] = domestic_checkbox
                st.session_state["international"] = international_checkbox
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.session_state.service_data = {
                    'service_info': service_info,
                    'total_fee': total_fee,
                    'timestamp': timestamp
                }
                st.session_state["page"] = "payment_info"

# 페이지 3: 결제 안내
def payment_page():
    st.title("수수료 계산")
    
    # 세션에서 데이터 가져오기
    service_data = st.session_state.get('service_data', {})
    if not service_data:
        st.error("서비스 데이터가 없습니다. 이전 화면으로 돌아가세요.")
        return
    
    total_fee = service_data['total_fee']  # 기본 수수료
    service_info = service_data['service_info']
    
    # 비용 계산 상세화
    email_data = service_info.get('email', {})
    domestic_data = service_info.get('domestic', [])
    international_data = service_info.get('international_post', [])
    
    email_count = len(email_data.get('recipients', []))
    domestic_count = len(domestic_data)
    international_count = len(international_data)
    
    # 추가 발급 수수료 계산
    additional_fee = 0  # 추가 발급 수수료
    
    # 이메일은 서류 1장만 발급되므로 추가 수수료는 없음
    for domestic in domestic_data:
        if domestic.get('documents', 0) > 1:
            additional_fee += (domestic['documents'] - 1) * 1000
    
    for international in international_data:
        if international.get('documents', 0) > 1:
            additional_fee += (international['documents'] - 1) * 1000
    
    st.write("비용 계산 상세:")
    if email_count > 0:
        st.write(f"- 이메일 신청 발급 건수 {email_count}건 * 2,000원 = {email_count * 2000}원")
    if domestic_count > 0:
        st.write(f"- 국내 우편 신청 발급 건수 {domestic_count}건 * 4,000원 = {domestic_count * 4000}원")
    if international_count > 0:
        st.write(f"- 해외 우편 신청 발급 건수 {international_count}건 * 50,000원 = {international_count * 50000}원")
    if additional_fee > 0:
        st.write(f"- 추가 발급 수수료 = {additional_fee}원")

    # 최종 수수료: 기본 수수료 + 추가 발급 수수료
    st.write(f"### 총 수수료: {total_fee}원")
    
    # 결제 안내 및 증빙 첨부
    st.write("아래와 같이 수수료를 납부하고 결제 증빙을 업로드해주세요.\n결제 증빙을 업로드한 후, 제출 버튼을 눌러주세요.")
    uploaded_file = st.file_uploader("첨부 파일 업로드", type=["jpg", "png", "pdf"])
    
    # 버튼 처리
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("이전"):
            st.session_state["page"] = "service_selection"
    with col2:
        if st.button("제출"):
            if uploaded_file:
                st.session_state["page"] = "submit_complete"
            else:
                st.error("결제 증빙을 업로드 해주세요.")

# 페이지 4: 제출 완료
def submit_complete_page():
    st.title("제출 완료")
    st.write("성공적으로 신청되었습니다. 감사합니다!")
    if st.button("홈으로"):
        st.session_state["page"] = "student_info"

# 메인 실행 함수
def main():
    # 세션 상태에서 현재 페이지 가져오기
    if "page" not in st.session_state:
        st.session_state["page"] = "student_info"

    # 페이지 전환
    if st.session_state["page"] == "student_info":
        student_info_page()
    elif st.session_state["page"] == "service_selection":
        service_selection_page()
    elif st.session_state["page"] == "payment_info":
        payment_page()
    elif st.session_state["page"] == "submit_complete":
        submit_complete_page()

if __name__ == "__main__":
    main()