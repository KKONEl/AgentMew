import json

state = {"goal": "draft E7", "constraints": ["never send"],
         "pending": ["verify stock"], "refs": ["mail:E7"]}
protected = json.dumps(state, sort_keys=True, separators=(",", ":"))
candidates = [("evidence", "stock=unknown"),
              ("recent", "user:continue"), ("old_history", "x" * 100)]
budget = len(protected) + 30
selected = [("state", protected)]
used = len(protected)
for name, text in candidates:
    if used + len(text) <= budget:
        selected.append((name, text))
        used += len(text)
assert used <= budget
names = [name for name, _ in selected]
assert names == ["state", "evidence", "recent"]
restored = json.loads(selected[0][1])
assert "never send" in restored["constraints"]
assert restored["pending"] == ["verify stock"]
print("selected:", ",".join(names))
print("constraint:", restored["constraints"][0])
print("next step:", restored["pending"][0])
