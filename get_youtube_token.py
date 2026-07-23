import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    print("=== الحصول على توكن يوتيوب الأبدي ===")
    print("يرجى إدخال البيانات التالية من حسابك في Google Cloud (قسم Credentials):")
    client_id = input("أدخل Client ID: ").strip()
    client_secret = input("أدخل Client Secret: ").strip()

    if not client_id or not client_secret:
        print("خطأ: يجب إدخال البيانات.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "youtube-bot",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl"
    ]
    flow = InstalledAppFlow.from_client_config(client_config, scopes)
    print("\nسيتم الآن فتح متصفحك لتسجيل الدخول والموافقة...")
    creds = flow.run_local_server(port=0)

    print("\n=============================================")
    print("✅ تم الحصول على الـ REFRESH TOKEN بنجاح!")
    print("انسخ السطر التالي وضعه في GitHub Secrets كـ YOUTUBE_REFRESH_TOKEN:")
    print("---------------------------------------------")
    print(creds.refresh_token)
    print("=============================================")

if __name__ == '__main__':
    main()
