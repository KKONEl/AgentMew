sources = {"students":{"A","B"}, "project":{"B","C"}}
state = {"facts":{}, "attempts":0, "trace":[]}
for need in ("students", "project"):
    if state["attempts"] >= 2:
        break
    state["attempts"] += 1
    state["facts"][need] = sources[need]
    state["trace"].append(need)
    print(f"step{state['attempts']}: retrieve {need}")
if {"students","project"} <= state["facts"].keys():
    answer = sorted(state["facts"]["students"] & state["facts"]["project"])
    print("answer:", ",".join(answer))
    assert answer == ["B"]
else:
    print("insufficient evidence")
assert state["attempts"] <= 2
