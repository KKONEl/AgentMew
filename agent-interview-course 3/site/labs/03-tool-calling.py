ledger = {}
orders = {"A17": {"tenant": "t1", "refundable": 1000}}

def refund(identity, order_id, cents, key, lose_response=False):
    if type(cents) is not int or cents <= 0:
        raise ValueError("invalid amount")
    order = orders[order_id]
    if order["tenant"] != identity:
        raise PermissionError("denied")
    scoped_key = (identity, key)
    payload = (order_id, cents)
    if scoped_key in ledger:
        old_payload, result = ledger[scoped_key]
        if payload != old_payload:
            raise ValueError("idempotency conflict")
        return result
    if cents > order["refundable"]:
        raise ValueError("over limit")
    order["refundable"] -= cents
    result = "confirmed"
    ledger[scoped_key] = (payload, result)
    if lose_response:
        raise TimeoutError("unknown to caller")
    return result

try:
    refund("t1", "A17", 300, "r1", lose_response=True)
except TimeoutError:
    print("first response: unknown")
assert refund("t1", "A17", 300, "r1") == "confirmed"
assert orders["A17"]["refundable"] == 700
print("retry: confirmed; remaining:", orders["A17"]["refundable"])
for identity, amount in [("t1", 400), ("t2", 300)]:
    try:
        refund(identity, "A17", amount, "r1")
    except (ValueError, PermissionError) as exc:
        print(type(exc).__name__ + ": " + str(exc))
assert len(ledger) == 1
