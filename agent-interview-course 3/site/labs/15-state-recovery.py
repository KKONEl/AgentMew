import sqlite3

db = sqlite3.connect(":memory:")
db.executescript("""
CREATE TABLE task(id TEXT PRIMARY KEY, status TEXT, receipt TEXT);
CREATE TABLE outbox(event_id TEXT PRIMARY KEY, sent INTEGER DEFAULT 0);
""")
with db:
    db.execute("INSERT INTO task VALUES (?, ?, NULL)", ("order-17", "intent"))
    db.execute("INSERT INTO outbox(event_id) VALUES (?)", ("order-17:create",))
remote = {}
def create_ticket(key):
    if key not in remote:
        remote[key] = "T" + str(len(remote) + 1)
    return remote[key]

key = "order-17:create"
create_ticket(key)  # 远端完成；模拟回执尚未保存便崩溃
with db:
    db.execute("UPDATE task SET status='unknown' WHERE id='order-17'")
print("after_timeout=" + db.execute("SELECT status FROM task").fetchone()[0])
receipt = create_ticket(key)  # 恢复时复用同一业务键
with db:
    db.execute("UPDATE task SET status='done', receipt=?", (receipt,))
    db.execute("UPDATE outbox SET sent=1 WHERE event_id=?", (key,))
# 模拟投递回执再次丢失，重复消费仍不会新增业务对象
assert create_ticket(key) == receipt
assert len(remote) == 1
assert db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1
assert db.execute("SELECT status, receipt FROM task").fetchone() == ("done", "T1")
print("remote_tickets=" + str(len(remote)))
print("receipt=" + receipt)
print("state=done")
