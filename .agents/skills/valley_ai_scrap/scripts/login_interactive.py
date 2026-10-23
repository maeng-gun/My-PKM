import os
import sys
from playwright.sync_api import sync_playwright

AUTH_FILE = "auth_state.json"
LOGIN_URL = "https://www.valley.town/login"
LOUNGE_URL = "https://www.valley.town/premium/lounge"

def load_env():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

def main():
    load_env()
    email = os.getenv("VALLEY_EMAIL", "")
    password = os.getenv("VALLEY_PASSWORD", "")

    print("=" * 60)
    print("Valley AI 대화형 브라우저 로그인 도구")
    print("브라우저 창이 열리면 로그인을 완료해주세요. (카카오/이메일 모두 가능)")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        # 만약 이메일과 패스워드가 있으면 기본값 자동 입력 시도
        if email:
            try:
                page.fill('input[name="email"]', email)
            except Exception:
                pass

        print("[안내] 브라우저 화면에서 로그인을 진행해주세요. 로그인이 완료되면 자동으로 세션이 저장됩니다.")

        # 로그인 성공 대기 (URL이 /login을 벗어나거나 lounge에 도달할 때까지 최대 120초)
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=120000)
            page.wait_for_timeout(3000)
            context.storage_state(path=AUTH_FILE)
            print(f"[성공] 로그인 성공! 세션이 {AUTH_FILE}에 안전하게 저장되었습니다.")
        except Exception as e:
            print(f"[타임아웃/오류] 2분 내에 로그인이 완료되지 않았습니다: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
