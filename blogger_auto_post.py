import os
import json
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# 1. 제미나이(작가 로봇) API 키
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# 2. 구글 블로거 OAuth2 클라이언트 JSON 내용 전체
GCP_CLIENT_SECRET_JSON_STR = os.environ.get('GCP_CLIENT_SECRET')
# 3. 구글 블로거 영구 출입증(Refresh Token)
GCP_REFRESH_TOKEN = os.environ.get('GCP_REFRESH_TOKEN')

# 최신 제미나이 로봇 준비!
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 구글 블로거 출입 권한
SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_service():
    """친구의 구글 블로거 가게에 들어갈 수 있는 마스터키(서비스)를 만듭니다."""
    try:
        client_config = json.loads(GCP_CLIENT_SECRET_JSON_STR)

        if 'installed' in client_config:
            creds_info = client_config['installed']
        elif 'web' in client_config:
            creds_info = client_config['web']
        else:
            raise ValueError("GCP_CLIENT_SECRET이 올바른 JSON 형식이 아닙니다.")

        creds = Credentials(
            token=None,
            refresh_token=GCP_REFRESH_TOKEN,
            client_id=creds_info['client_id'],
            client_secret=creds_info['client_secret'],
            token_uri=creds_info['token_uri'],
            scopes=SCOPES
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("인증 실패! 열쇠(Refresh Token)가 잘못되었거나 만료되었습니다.")

        service = build('blogger', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"[오류] 블로거 열쇠 문제 발생: {e}")
        return None

def generate_content():
    """제미나이(작가 로봇)에게 블로그 글을 써달라고 부탁합니다."""
    print("최신 제미나이 로봇에게 글 부탁하는 중...")
    prompt = """
    당신은 '초등학생도 이해할 수 있는 재미있는 IT 기술과 과학 상식' 블로그의 주인입니다.
    오늘 블로그에 올릴 글을 '제목'과 '본문'으로 나누어서 써주세요.

    [요구사항]
    1. 주제: '최신 IT 기술'이나 '신기한 과학 상식' 중 하나.
    2. 말투: 초등학생 친구에게 이야기하듯 친근하게.
    3. 형식:
       - 출력은 반드시 JSON 형식: {"title": "글 제목", "content": "글 본문 HTML"}
       - "content"는 <h1>, <p>, <strong> 등 HTML 태그 사용.
       - 이모티콘 적극 사용.
    """
    try:
        # 최신 코드 적용!
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        full_text = response.text.strip()
        
        if full_text.startswith("```json"):
            full_text = full_text.replace("```json", "").replace("```", "").strip()

        content_json = json.loads(full_text)
        return content_json['title'], content_json['content']
    except Exception as e:
        print(f"[오류] 제미나이 에러: {e}")
        return "오류 발생 😢", "<p>글을 쓰지 못했어요!</p>"

def post_to_blogger(service, title, content):
    """블로그에 글 올리기"""
    print(f"블로그에 글을 올리는 중... 제목: {title}")
    try:
        blogs_response = service.blogs().list(userId='me').execute()
        if 'items' not in blogs_response or not blogs_response['items']:
            print("[오류] 블로그가 없습니다!")
            return False

        blog_id = blogs_response['items'][0]['id']
        post_data = {'kind': 'blogger#post', 'title': title, 'content': content}
        posts_response = service.posts().insert(blogId=blog_id, body=post_data, isDraft=False).execute()

        print(f"[성공] 글이 자동으로 올라갔어요! URL: {posts_response['url']}")
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
