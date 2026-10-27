from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AI
    gemini_api_key: str = ""
    
    # App
    app_secret_key: str = "change-me-in-production"
    upload_dir: str = "uploads"
    # Public URL of this server — required by Instagram Graph API (video must be publicly reachable)
    # For local testing keep http://localhost:8000; set to your deployed domain in production
    public_base_url: str = "http://localhost:8000"
    
    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    
    # Meta (Instagram + Facebook)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    
    # TikTok
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    
    # Twitter/X
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()