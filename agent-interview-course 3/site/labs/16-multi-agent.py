from dataclasses import dataclass

@dataclass(frozen=True)
class Result:
    task_id: str
    source_version: int
    evidence: tuple
    finding: str

def research():
    return Result("capacity", 3, ("load-test-v3",), "capacity_ok")
def review():
    return Result("permission", 3, ("acl-test-v3",), "permission_ok")

def validate(result, expected_version):
    return result.source_version == expected_version and bool(result.evidence)

budget = 2
results = {}
for worker in (research, review):
    assert budget > 0
    budget -= 1
    result = worker()
    assert validate(result, 3), "stale or ungrounded result"
    results.setdefault(result.task_id, result)  # 重复消息不增加完成数
assert len(results) == 2 and budget == 0
stale = Result("capacity", 2, ("old-test",), "capacity_ok")
assert not validate(stale, 3)
# 确定性终止：预算耗尽后不允许新增一轮“专家讨论”
can_dispatch_again = budget > 0
assert not can_dispatch_again
print("accepted=" + ",".join(sorted(results)))
print("stale_rejected=True")
print("remaining_budget=" + str(budget))
print("terminated=all_required_results_verified")
