def run(actions, limit=4):
    seen = set()
    observations = []
    for step, action in enumerate(actions, 1):
        if step > limit:
            return "budget_exhausted", observations
        if action == "finish":
            return ("success" if "evidence" in observations else "incomplete"), observations
        observation = "evidence" if action == "inspect" else "empty"
        signature = (action, observation)
        if signature in seen:
            return "no_progress", observations
        seen.add(signature)
        observations.append(observation)
    return "incomplete", observations

ok = run(["search", "inspect", "finish"])
stuck = run(["search", "search", "finish"])
short = run(["search", "inspect", "finish"], limit=1)
assert ok[0] == "success"
assert stuck[0] == "no_progress"
assert short[0] == "budget_exhausted"
print("normal:", ok[0])
print("repeated:", stuck[0])
print("limited:", short[0])
