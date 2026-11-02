def metrics(ranking, relevant, k):
    top = ranking[:k]
    recall = len(set(top) & relevant) / len(relevant) if relevant else None
    rr = next((1 / i for i, d in enumerate(top, 1) if d in relevant), 0)
    return recall, rr

recall, rr = metrics(["X","A","Y"], {"A","B"}, 3)
assert recall == 0.5 and rr == 0.5
print(f"Recall@3={recall:.2f}, RR@3={rr:.2f}")
r2, rr2 = metrics(["A","B","X"], {"A","B"}, 3)
print(f"Recall@3={r2:.2f}, RR@3={rr2:.2f}")
assert metrics(["X"], set(), 1)[0] is None
