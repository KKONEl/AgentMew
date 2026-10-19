from unstructured.partition.auto import partition

from config import DATA_SOURCE_DIR

# PDF文件路径
pdf_path = DATA_SOURCE_DIR / "24-大模型（LLMs）RAG 优化策略 —— RAG-Fusion篇.pdf"

# 使用Unstructured加载并解析PDF文档
elements = partition(
    filename=str(pdf_path),
    content_type="application/pdf"
)
element = elements[0]

print(element.category)
print(element.text[:100])
print(element.metadata.page_number)
print(element.metadata.to_dict().keys())

print("----------")

# 打印解析结果
print(f"解析完成: {len(elements)} 个元素, {sum(len(str(e)) for e in elements)} 字符")

# 统计元素类型
from collections import Counter
types = Counter(e.category for e in elements)
print(f"元素类型: {dict(types)}")

# 显示所有元素
print("\n所有元素:")
for i, element in enumerate(elements, 1):
    print(f"Element {i} ({element.category}):")
    print(element)
    print("=" * 60)