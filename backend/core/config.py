"""
FormulaBase Nexus - Core Configuration
App Settings, License Validation, and Encryption
"""
import os
import uuid
import hashlib
import platform
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


def get_hardware_id() -> str:
    """Generate a unique Hardware ID for license binding."""
    machine_id_parts = [
        platform.node(),
        platform.machine(),
        platform.processor(),
        str(uuid.getnode()),  # MAC address
    ]
    raw = "-".join(part for part in machine_id_parts if part)
    return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()


class Settings(BaseSettings):
    # App Identity
    APP_NAME: str = "FormulaBase Nexus"
    APP_VERSION: str = "1.0.0"
    APP_SUBTITLE: str = "Multi-Brand POS & Formula-Based OEM ERP"
    COMPANY_NAME: str = "Formula Base OEM Services Myanmar"

    # API Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8765
    DEBUG: bool = True
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "tauri://localhost"]

    # Security
    SECRET_KEY: str = Field(
        default="formulabase-nexus-super-secret-jwt-key-2024-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_URL: str = Field(default="", env="DATABASE_URL")

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        db_path = os.path.join(self.BASE_DIR, "database", "formulabase.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"

    # File paths
    @property
    def templates_dir(self) -> str:
        path = os.path.join(self.BASE_DIR, "modules", "pdf_invoice_engine", "templates")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def fonts_dir(self) -> str:
        path = os.path.join(self.BASE_DIR, "modules", "pdf_invoice_engine", "fonts")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def invoices_output_dir(self) -> str:
        path = os.path.join(self.BASE_DIR, "data", "invoices_output")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def uploads_dir(self) -> str:
        path = os.path.join(self.BASE_DIR, "data", "uploads")
        os.makedirs(path, exist_ok=True)
        return path

    # License
    HARDWARE_ID: str = Field(default_factory=get_hardware_id)
    LICENSE_MODE: str = "TRIAL"  # TRIAL | PRO | ENTERPRISE
    TRIAL_INVOICE_LIMIT: int = 50

    # AI / Telegram (set via environment or settings UI)
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_OWNER_CHAT_ID: str = Field(default="", env="TELEGRAM_OWNER_CHAT_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
