from pydantic import model_validator
from pydantic_settings import BaseSettings as Base, SettingsConfigDict



class Settings(Base):

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )

    # ———————— APP Info ————————
    app_title: str = 'FastAPI Base Structure For Beginning'
    app_version: str = '1.0.0'
    app_description: str = 'placeholder'
    # ————————————————————————————
    

    # ———————— DB & SERVER ————————
    host: str = '127.0.0.1'
    port: int = 8000
    reload: bool = False
    allowed_origins: list[str] = ['*']
    allowed_headers: list[str] = ['*']
    allow_methods: list[str] = ['GET', 'POST', 'PATCH', 'DELETE']
    environment: str = 'dev' # dev - pro

    api_prefix: str = '/api/v1'

    database_url: str = 'sqlite+aiosqlite:///./database.db'
    echo: bool = False

    autoflush: bool = False
    expire_on_commit: bool = False
    # ————————————————————————————



    # ———————— JWT ————————
    access_secret_key: str = 'placeholder-change-it-in-production-mode'
    refresh_secret_key: str = 'placeholder-change-it-in-production-mode'
    algorithm: str = 'HS256'

    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 30
    # ————————————————————————————


    @model_validator(mode='after')
    def _validate_production_secrets(self) -> "Settings":

        if self.environment != 'pro':
            return self

        attrs = (
            'access_secret_key',
            'refresh_secret_key'
        )

        for attr in attrs:
            value: str = getattr(self, attr)
            if value.startswith('placeholder-change-it-in-production-mode'):
                raise ValueError(
                    f"FATAL: {attr} contans a placeholder value. "
                    f"Set a real secret in `.env` before running in production mode."
                )

        if self.echo:
            raise ValueError(
                "FATAL: `ECHO` must be False in production to prevent SQL statement leaks."
            )

        return self

settings = Settings()