from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    blender_path: str = "/Applications/Blender.app/Contents/MacOS/Blender"
    pipeline_root: Path = Path(__file__).parent / "scripts"
    staging_dir: Path = Path(__file__).parent.parent / "data" / "staging"
    output_dir: Path = Path(__file__).parent.parent / "data" / "output"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
