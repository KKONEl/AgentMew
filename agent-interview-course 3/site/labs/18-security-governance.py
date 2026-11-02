import hashlib
import json

session = {"user": "u1", "tenant": "A", "tools": {"send_report"}}
def fingerprint(action):
    raw = json.dumps(action, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()

def authorize(action, approval):
    if action["tool"] not in session["tools"]:
        return False, "tool_denied"
    if action["resource_tenant"] != session["tenant"]:
        return False, "tenant_denied"
    if action["recipient"] != "audit@company.local":
        return False, "recipient_denied"
    if fingerprint(action) != approval:
        return False, "approval_mismatch"
    return True, "allowed"

safe = {"tool": "send_report", "resource_tenant": "A",
        "resource": "report-v3", "recipient": "audit@company.local"}
approval = fingerprint(safe)
attack = dict(safe, resource_tenant="B")
changed = dict(safe, resource="secret-contract")
checks = [authorize(attack, approval), authorize(changed, approval),
          authorize(safe, approval)]
assert checks == [(False, "tenant_denied"), (False, "approval_mismatch"),
                  (True, "allowed")]
executed = [action for action in (attack, changed, safe)
            if authorize(action, approval)[0]]
assert executed == [safe]
for ok, reason in checks:
    print("ALLOW" if ok else "DENY", reason)
print("executed=" + str(len(executed)))
