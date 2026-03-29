import os
import json
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# --- [설정 영역] 비밀 금고(Secrets)에서 열쇠 가져오기 ---
# 1. 제미나이(작가 로봇) API 키
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# 2. 구글 블로거 OAuth2 클라이언트 JSON 내용 전체 (복잡한 JSON 형태여야 함)
GCP_CLIENT_SECRET_JSON_STR = os.environ.get('GCP_CLIENT_SECRET')
# 3. 구글 블로거 영구 출입증(Refresh Token)
GCP_REFRESH_TOKEN = os.environ.get('GCP_REFRESH_TOKEN')

# 제미나이 로봇에게 API 키를 건네주고 준비시킵니다.
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# 구글 블로거 가게에 글을 쓰기 위한 출입 권한(SCOPES)입니다.
SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_blogger_service():
    """친구의 구글 블로거 가게에 들어갈 수 있는 마스터키(서비스)를 만듭니다."""
    try:
        # 1. 비밀 금고에서 가져온 복잡한 JSON 문자열을 로봇이 이해할 수 있는 딕셔너리로 바꿉니다.
        client_config = json.loads(GCP_CLIENT_SECRET_JSON_STR)

        # 2. JSON 내용 안에 있는 클라이언트 ID와 비밀번호를 찾습니다.
        # 구글에서 받은 JSON 파일은 보통 'installed'나 'web'으로 시작합니다.
        if 'installed' in client_config:
            creds_info = client_config['installed']
        elif 'web' in client_config:
            creds_info = client_config['web']
        else:
            raise ValueError("GCP_CLIENT_SECRET 시크릿은 구글 콘솔에서 다운받은 JSON 파일 내용 전체여야 합니다.")

        # 3. 영구 출입증(GCP_REFRESH_TOKEN)과 클라이언트 정보를 합쳐서 '영구 출입증(Credentials)'을 완성합니다.
        creds = Credentials(
            token=None, # 영구 출입증이 있으므로 처음 임시 토큰은 비워둡니다.
            refresh_token=GCP_REFRESH_TOKEN,
            client_id=creds_info['client_id'],
            client_secret=creds_info['client_secret'],
            token_uri=creds_info['token_uri'],
            scopes=SCOPES
        )

        # 4. 출입증이 만료되었는지 확인하고, 만료되었다면 영구 출입증으로 새 임시 마스터키(Access Token)를 받아옵니다.
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("블로거 로그인(인증)에 실패했습니다. 열쇠를 확인해주세요.")

        # 5. 이제 로그인된 상태로 블로거 서비스를 만듭니다. (이게 진짜 마스터키)
        service = build('blogger', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"[오류] 블로거 가게에 들어가는 열쇠를 만드는 중 문제가 생겼어요: {e}")
        return None

def generate_content():
    """제미나이(작가 로봇)에게 블로그 글을 써달라고 부탁합니다."""
    print("제미나이 로봇에게 재미있는 글을 부탁하는 중...")
    
    # 제미나이에게 시킬 구체적인 명령입니다.
    prompt = """
    당신은 '초등학생도 이해할 수 있는 재미있는 IT 기술과 과학 상식' 블로그의 주인입니다.
    오늘 블로그에 올릴 글을 '제목'과 '본문'으로 나누어서 써주세요.

    [요구사항]
    1. 주제: '최신 IT 기술(예: AI, 로봇, 메타버스)'이나 '신기한 과학 상식' 중 하나를 선택해서 아주 재미있게 써주세요.
    2. 말투: 초등학생 친구에게 이야기하듯 친근하고 재미있는 말투를 써주세요.
    3. 형식:
       - 출력은 반드시 JSON 형식으로 해주세요: {"title": "글 제목", "content": "글 본문 HTML"}
       - "content" 부분은 반드시 예쁜 HTML 형식으로 만들어주세요 (예: <h1>, <p>, <ul>, <li>, <strong> 태그 사용).
       - 본문에는 글의 주제와 어울리는 이모티콘(emojis)을 많이 사용해주세요.
       - 본문에는 중요한 단어에 <strong> 태그를 사용해서 강조해주세요.
    """
    try:
        response = model.generate_content(prompt)
        # 제미나이가 준 결과에서 JSON 부분만 추출합니다.
        full_text = response.text.strip()
        # 마크다운 블록(```json ... ```) 제거
        if full_text.startswith("```json"):
            full_text = full_text.replace("```json", "").replace("```", "").strip()

        content_json = json.loads(full_text)
        return content_json['title'], content_json['content']
    except Exception as e:
        print(f"[오류] 제미나이 작가 로봇이 글쓰기를 거부했거나 오류가 생겼어요: {e}")
        # 오류 발생 시 임시 글 반환
        return "오늘의 과학 상식을 가져오지 못했어요 😢", "<p>로봇이 글을 가져오다가 오류가 생겼대요. 나중에 다시 시도해봐요!</p>"

def post_to_blogger(service, title, content):
    """작성된 글을 블로거 가게에 자동으로 진열(게시)합니다."""
    print(f"블로그에 글을 올리는 중... 제목: {title}")
    try:
        # 1. 로그인된 내 계정의 블로그 목록을 가져옵니다.
        blogs_request = service.blogs().list(userId='me')
        blogs_response = blogs_request.execute()

        if 'items' not in blogs_response or not blogs_response['items']:
            print("[오류] 이 구글 계정에는 블로거 블로그가 없어요!")
            return False

        # 첫 번째 블로그를 선택합니다. (대부분의 친구들은 블로그가 하나일 테니까요)
        blog_id = blogs_response['items'][0]['id']
        blog_name = blogs_response['items'][0]['name']
        print(f"[{blog_name}] 블로그(ID: {blog_id})에 글을 올립니다.")

        # 2. 블로거에 올릴 글의 데이터를 만듭니다.
        post_data = {
            'kind': 'blogger#post',
            'title': title,
            'content': content,
        }

        # 3. 글을 올립니다 (isDraft=False 면 바로 전 세계에 발행됩니다).
        posts_request = service.posts().insert(blogId=blog_id, body=post_data, isDraft=False)
        posts_response = posts_request.execute()

        print(f"[성공] 블로그 글이 자동으로 올라갔어요! 주소: {posts_response['url']}")
        return True
    except Exception as e:
        print(f"[오류] 블로거에 글을 올리는 중 문제가 생겼어요: {e}")
        return False

# --- [로봇 작동 영역] 프로그램의 시작점 ---
if __name__ == "__main__":
    print("===== 자동 블로그 포스팅 로봇 작동 시작 =====")
    
    # 1. 블로거 가게에 들어갈 열쇠를 만듭니다.
    blogger_service = get_blogger_service()

    if blogger_service:
        # 2. 제미나이(작가 로봇)에게 글을 쓰게 합니다.
        blog_title, blog_content = generate_content()

        # 3. 써온 글을 블로거 가게에 발행합니다.
        post_to_blogger(blogger_service, blog_title, blog_content)
    else:
        print("[실패] 블로거 가게에 들어가는 데 실패해서 종료합니다.")
        
    print("===== 자동 블로그 포스팅 로봇 작동 종료 =====")
