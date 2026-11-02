records = [
    {"tenant": "A", "key": "style", "text": "Chinese examples", "expires": 100, "version": 1},
    {"tenant": "B", "key": "style", "text": "English examples examples", "expires": 100, "version": 1},
    {"tenant": "A", "key": "address", "text": "old examples", "expires": 5, "version": 1},
]

def retrieve(runtime_tenant, query, now):
    allowed = [r for r in records if r["tenant"] == runtime_tenant
               and r["expires"] > now and not r.get("deleted", False)]
    return sorted(allowed, key=lambda r: -r["text"].lower().count(query.lower()))

def update(runtime_tenant, key, text):
    matches = [r for r in records if r["tenant"] == runtime_tenant and r["key"] == key]
    assert len(matches) == 1
    matches[0]["text"] = text
    matches[0]["version"] += 1

found = retrieve("A", "examples", now=10)
assert len(found) == 1 and found[0]["tenant"] == "A"
print("A retrieval:", found[0]["text"])
update("A", "style", "English examples")
found = retrieve("A", "examples", now=10)
assert found[0]["version"] == 2
print("A updated:", found[0]["text"], "version", found[0]["version"])
found[0]["deleted"] = True
assert retrieve("A", "examples", now=10) == []
assert retrieve("B", "examples", now=10)[0]["version"] == 1
print("A after delete:", len(retrieve("A", "examples", now=10)))
print("B unchanged:", retrieve("B", "examples", now=10)[0]["version"])
