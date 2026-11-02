docs = [
 {"id":"old", "tokens":{"上海","住宿","标准"}, "year":2025,"limit":400},
 {"id":"new", "tokens":{"上海","住宿","标准"}, "year":2026,"limit":500},
 {"id":"food", "tokens":{"上海","餐饮"}, "year":2026,"limit":100},
]
query = {"上海", "住宿", "标准"}
allowed = [d for d in docs if d["year"] == 2026]
ranked = sorted(allowed, key=lambda d: len(query & d["tokens"]), reverse=True)
evidence = ranked[0]
assert evidence["id"] == "new"
print(f"答案：{evidence['limit']}元/晚；引用：{evidence['id']}")
