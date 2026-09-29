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

# tool 预算
TOOL_RESULT_BUDGET = 200_000
# 单条结果预算
LARGE_RESULT_CHAR_LIMIT = 30_000
# 上下文预览长度
PREVIEW_CHAR_LIMIT = 2_000
CONTEXT_CHAR_LIMIT = 50_000
COMPACT_TARGET_CHAR_LIMIT = 40_000
# 限制额外摘要调用读取的历史长度，避免摘要请求自身超出上下文。
SUMMARY_INPUT_CHAR_LIMIT = 80_000

# 压缩配置
MAX_HISTORY_MESSAGES = 50
KEEP_HEAD_MESSAGES = 3
KEEP_TAIL_MESSAGES = 46
# micro compact 保留最近已读结果；API 超限补救保留最近消息且只重试一次。
KEEP_RECENT_RESULTS = 3
KEEP_RECENT_MESSAGES = 5
MAX_REACTIVE_RETRIES = 1
