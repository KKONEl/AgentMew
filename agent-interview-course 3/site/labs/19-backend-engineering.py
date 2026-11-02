database = {"value": "old", "version": 7}
cache = {}
watermark = {"item": 7}

def fill(key, value, version):
    # 真实共享服务需将比较与写入做成原子操作
    if version < watermark.get(key, 0):
        return False
    current = cache.get(key)
    if current and version < current["version"]:
        return False
    cache[key] = {"value": value, "version": version}
    return True

old_read = dict(database)  # R读取后暂停
# W在数据库提交新值，并把失效水位推进到8
database.update(value="new", version=8)
watermark["item"] = 8
cache.pop("item", None)
accepted_old = fill("item", old_read["value"], old_read["version"])
assert accepted_old is False and "item" not in cache
accepted_new = fill("item", database["value"], database["version"])
assert accepted_new is True
assert cache["item"] == {"value": "new", "version": 8}
print("old_fill=" + str(accepted_old))
print("new_fill=" + str(accepted_new))
print("cached=" + cache["item"]["value"])
print("version=" + str(cache["item"]["version"]))
