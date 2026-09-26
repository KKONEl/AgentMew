from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('api_key')
base_url = os.getenv('base_url')
model = os.getenv('model')