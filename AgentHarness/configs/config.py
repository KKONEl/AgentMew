from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('api_key')
base_url = os.getenv('base_url')
model = os.getenv('model')
todo_len = 20
subagent_loop = 30
HARNESS_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = HARNESS_DIR / "skills"