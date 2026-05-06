from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    blender_path: str = "/Applications/Blender.app/Contents/MacOS/Blender"
    pipeline_root: Path = Path(__file__).parent / "scripts"
    staging_dir: Path = ROOT_DIR / "data" / "staging"
    output_dir: Path = ROOT_DIR / "data" / "output"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
