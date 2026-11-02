reports = [
    [("A","检索"),("B","多Agent")],
    [("A","检索"),("C","检索")],
]
# Map输出已人工给定；用实体ID模拟Reduce去重。
merged = {}
for report in reports:
    for project, theme in report:
        merged.setdefault(theme, set()).add(project)
assert merged["检索"] == {"A","C"}
for theme in sorted(merged):
    print(theme, ",".join(sorted(merged[theme])))
