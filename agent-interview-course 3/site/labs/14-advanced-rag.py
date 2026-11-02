leaves = {"a":"检索延迟高", "b":"检索召回不足", "c":"工具需要权限"}
parents = {"检索质量": ["a","b"], "工具治理":["c"]}
query = "检索"
hits = [p for p in parents if query in p]
ids = [child for p in hits for child in parents[p]]
print("summary:", ",".join(hits))
for child in ids:
    print(child, leaves[child])
assert ids == ["a","b"]
