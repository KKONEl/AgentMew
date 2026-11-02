def kv_bytes(layers, kv_heads, head_dim, tokens, batch, element_bytes):
    return 2 * layers * kv_heads * head_dim * tokens * batch * element_bytes

def cost_per_success(total_cost, successes):
    if successes <= 0:
        return float("inf")
    return total_cost / successes

kv = kv_bytes(8, 2, 64, 1024, 4, 2)
assert kv == 16 * 1024 * 1024
assert kv_bytes(8, 2, 64, 1024, 8, 2) == kv * 2
# 单位为教学中的统一成本单位，不是任何供应商报价
base = cost_per_success(100, 90)
cheap = cost_per_success(80, 50)
assert cheap > base
start, first, last, output_tokens = 0.0, 0.6, 2.6, 101
ttft = first - start
tpot = (last - first) / (output_tokens - 1)
assert round(tpot, 3) == 0.02
arrival_per_second, mean_task_seconds = 2, 5
assert arrival_per_second * mean_task_seconds == 10
print(f"kv_mib={kv / (1024 ** 2):.1f}")
print(f"baseline_cost_per_success={base:.2f}")
print(f"cheap_cost_per_success={cheap:.2f}")
print(f"ttft_seconds={ttft:.2f}")
print(f"tpot_seconds={tpot:.3f}")
print("mean_inflight=10")
