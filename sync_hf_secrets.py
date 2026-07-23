import os
from huggingface_hub import HfApi

def sync_secrets():
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("❌ Error: HF_TOKEN is missing. Please add it to GitHub Secrets.")
        return

    api = HfApi(token=hf_token)
    repo_id = "mmossad824/sports-bot"

    secrets_to_sync = [
        "FB_PAGE_TOKEN",
        "FB_PAGE_ID",
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHANNEL_ID",
        "WEBSITE_URL"
    ]

    print(f"🔄 Syncing secrets to Hugging Face Space: {repo_id}")
    
    success_count = 0
    for secret in secrets_to_sync:
        val = os.environ.get(secret)
        if val:
            try:
                api.add_space_secret(repo_id=repo_id, key=secret, value=val)
                print(f"✅ Successfully synced: {secret}")
                success_count += 1
            except Exception as e:
                print(f"❌ Failed to sync {secret}: {e}")
        else:
            print(f"⚠️ Warning: {secret} is not set in environment, skipping.")

    print(f"\n🎉 Sync completed! Successfully synced {success_count} secrets.")

if __name__ == "__main__":
    sync_secrets()
