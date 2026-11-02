class Server:
    def __init__(self, label):
        self.label = label
    def list_tools(self):
        return [{"name": "search", "inputSchema": {"type": "object"}}]
    def call(self, request):
        assert request["method"] == "tools/call"
        assert request["params"]["name"] == "search"
        query = request["params"]["arguments"]["query"]
        return {"jsonrpc": "2.0", "id": request["id"],
                "result": {"text": self.label + ":" + query}}

servers = {"docs": Server("document"), "tickets": Server("ticket")}
routes = {}
for namespace, server in servers.items():
    for tool in server.list_tools():
        routes[namespace + "_" + tool["name"]] = (server, tool["name"])
model_call = {"id": "model-8", "name": "tickets_search", "arguments": {"query": "T42"}}
server, real_name = routes[model_call["name"]]
request = {"jsonrpc": "2.0", "id": 19, "method": "tools/call",
           "params": {"name": real_name, "arguments": model_call["arguments"]}}
response = server.call(request)
assert response["id"] == request["id"]
observation = {"tool_call_id": model_call["id"], "text": response["result"]["text"]}
assert observation["text"] == "ticket:T42"
print("available:", ",".join(sorted(routes)))
print("observation:", observation["tool_call_id"], observation["text"])
