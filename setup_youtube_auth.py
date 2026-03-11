"""
Jalankan file ini SEKALI di komputer lokal sebelum setup GitHub Actions.
Ini akan membuka browser untuk login Google dan menyimpan token ke youtube_token.json
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    # Download client_secrets.json dari Google Cloud Console:
    # APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=0)

    # Simpan token untuk dipakai GitHub Actions
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    with open("youtube_token.json", "w") as f:
        json.dump(token_data, f, indent=2)

    print("✅ Token berhasil disimpan ke youtube_token.json")
    print("   Sekarang upload isi file ini ke GitHub Secrets dengan nama: YOUTUBE_TOKEN_JSON")

if __name__ == "__main__":
    main()
