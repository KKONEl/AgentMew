from model import embedding
from vector_stores import VectorStoreService

service = VectorStoreService(embedding=embedding)

docs = service.search(
    query="RAG-Fusion 优势",
    k=5,
)

print(f"召回 {len(docs)} 个片段")

for i, doc in enumerate(docs, start=1):
    print(f"\n--- 结果 {i} ---")
    print("文本：", doc.page_content[:200])
    print("来源：", doc.metadata.get("source", "未知"))
    print("页码：", doc.metadata.get("page_number", "无"))