import random
from collections import Counter

candidates = ["paid", "pending", "unknown"]
weights = [0.6, 0.3, 0.1]
greedy = candidates[max(range(len(weights)), key=weights.__getitem__)]
rng = random.Random(7)
samples = rng.choices(candidates, weights=weights, k=100)
counts = Counter(samples)
assert greedy == "paid"
assert len(counts) == 3
window, reserved_output = 100, 20
parts = {"rules": 10, "tools": 15, "history": 35, "evidence": 20}
assert sum(parts.values()) + reserved_output == window
print("greedy:", greedy)
print("sampled categories:", ",".join(sorted(counts)))
print("input budget:", window - reserved_output)
print("fact verified:", False)
