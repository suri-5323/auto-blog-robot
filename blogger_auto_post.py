import os
import json
import urllib.request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# --- [설정 영역] 비밀 금고에서 열쇠 가져오기 ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GCP_CLIENT_SECRET_JSON_STR = os.environ.get('GCP_CLIENT_SECRET')
GCP_REFRESH_TOKEN = os.environ.get('GCP_REFRESH_TOKEN')

# 🚨 [여기 꼭 수정!] 아까 복사한 내 블로그의 긴 숫자 ID를 아래 따옴표 안에 넣어주세요!
BLOG_ID = '6357492878197807658'

SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_service():
    """구글 블로거 마스터키를 만듭니다."""
    try:
        client_config = json.loads(GCP_CLIENT_SECRET_JSON_STR)
        creds_info = client_config.get('installed', client_config.get('web'))
        
        creds = Credentials(
            token=None,
            refresh_token=GCP_REFRESH_TOKEN,
            client_id=creds_info['client_id'],
            client_secret=creds_info['client_secret'],
            token_uri=creds_info['token_uri'],
            scopes=SCOPES
        )

        if not creds.valid:
            if creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("마스터키가 없습니다.")

        return build('blogger', 'v3', credentials=creds)
    except Exception as e:
        print(f"[오류] 블로거 열쇠 에러: {e}")
        return None

def generate_content():
    """제미나이에게 직접 전화를 걸어 글을 부탁합니다 (부품 충돌 방지 완벽 코드!)"""
    print("최신 제미나이 로봇에게 재미있는 글을 부탁하는 중...")
    prompt = """
    당신은 '초등학생도 이해할 수 있는 재미있는 IT 기술과 과학 상식' 블로그의 주인입니다.
    오늘 블로그에 올릴 글을 '제목'과 '본문'으로 나누어서 써주세요.
    [요구사항]
    1. 주제: '최신 IT 기술'이나 '신기한 과학 상식' 중 하나.
    2. 말투: 초등학생 친구에게 이야기하듯 친근하게.
    3. 형식: 반드시 JSON 형식 {"title": "글 제목", "content": "글 본문 HTML(<h1>,<p>등 사용)"}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            text = result['candidates'][0]['content']['parts'][0]['text']
            
            # 마크다운 찌꺼기 청소
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()
                
            content_json = json.loads(text)
            return content_json['title'], content_json['content']
    except Exception as e:
        print(f"[오류] 제미나이 에러: {e}")
        return "오류 발생 😢", "<p>글을 쓰지 못했어요!</p>"

def post_to_blogger(service, title, content):
    """지정해준 진짜 블로그 ID(주소)로 정확하게 글을 올립니다."""
    print(f"블로그에 글을 올리는 중... 제목: {title}")
    try:
        post_data = {'kind': 'blogger#post', 'title': title, 'content': content}
        # 헷갈리는 list() 대신 정확한 blogId로 바로 꽂아 넣습니다!
        posts_response = service.posts().insert(blogId=BLOG_ID, body=post_data, isDraft=False).execute()
        print(f"[성공] 글이 자동으로 올라갔어요! 주소: {posts_response['url']}")
        return True
    except Exception as e:
        print(f"[오류] 글 올리기 실패: {e}")
        return False

if __name__ == "__main__":
    print("===== 자동 블로그 포스팅 로봇 작동 시작 =====")
    blogger_service = get_blogger_service()
    if blogger_service:
        blog_title, blog_content = generate_content()
        post_to_blogger(blogger_service, blog_title, blog_content)
    else:
        print("[실패] 블로거 가게에 들어가는 데 실패해서 종료합니다.")
    print("===== 자동 블로그 포스팅 로봇 작동 종료 =====")
