"""Mock MCP discovery and host controlled tool dispatch (s14)."""

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class MCPClient:
    tools: list[dict] = field(default_factory=list)
    handlers: dict[str, Callable] = field(default_factory=dict)

    def call_tool(self, name: str, args: dict) -> str:
        try:
            return str(self.handlers[name](**args))
        except Exception as error:
            return f"MCP error: {type(error).__name__}: {error}"


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False}}


def _docs() -> MCPClient:
    docs = {
        "agent loop": "An agent loop sends messages and tools to the model, executes calls, and appends results.",
        "hooks": "Hooks observe lifecycle events before and after tool calls and at Stop.",
        "mcp": "MCP exposes server tools through discovery and call boundaries.",
    }
    return MCPClient(
        tools=[_tool("search", "Search mock documentation.",
                     {"query": {"type": "string"}}, ["query"]),
               _tool("get_version", "Get documentation API version.", {}, [])],
        handlers={"search": lambda query: "\n".join(
            f"{k}: {v}" for k, v in docs.items() if query.lower() in k or k in query.lower())
            or "No matches", "get_version": lambda: "docs-api/1.0"},
    )


def _deploy() -> MCPClient:
    return MCPClient(
        tools=[_tool("status", "Get mock deployment status.", {}, []),
               _tool("trigger", "Trigger mock deployment.",
                     {"environment": {"type": "string"}}, ["environment"])],
        handlers={"status": lambda: "web: healthy; deployment: idle",
                  "trigger": lambda environment: f"Mock deployment triggered for {environment}"},
    )


MOCK_SERVERS = {"docs": _docs, "deploy": _deploy}
HOST_POLICY = {("docs", "search"): "allow", ("docs", "get_version"): "allow",
               ("deploy", "status"): "allow", ("deploy", "trigger"): "confirm"}
_CONNECTED: dict[str, MCPClient] = {}
_APPROVED: set[tuple[str, str]] = set()


def normalize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def connect_mcp(name: str) -> str:
    if name in _CONNECTED:
        return f"MCP server '{name}' already connected"
    factory = MOCK_SERVERS.get(name)
    if factory is None:
        return f"Unknown MCP server '{name}'"
    candidate = dict(_CONNECTED)
    candidate[name] = factory()
    # Validate every generated name before making the connection visible.
    _assemble([], {}, candidate)
    _CONNECTED[name] = candidate[name]
    return f"Connected {name}: {', '.join(t['name'] for t in candidate[name].tools)}"


def approve_mcp_tool(server: str, tool: str) -> None:
    """Host-only approval; the model has no tool that calls this function."""
    _APPROVED.add((server, tool))


def _assemble(base_tools: list[dict], base_handlers: dict, clients: dict):
    tools = list(base_tools)
    handlers = dict(base_handlers)
    origins = {tool["function"]["name"] for tool in tools}
    for server_name, client in clients.items():
        for definition in client.tools:
            raw_name = definition["name"]
            name = f"mcp__{normalize_name(server_name)}__{normalize_name(raw_name)}"
            if len(name) > 64 or name in origins:
                raise ValueError(f"MCP tool name collision or length overflow: {name}")
            origins.add(name)
            tools.append({"type": "function", "function": {
                "name": name, "description": definition.get("description", ""),
                "parameters": definition.get("inputSchema", {"type": "object", "properties": {}})}})
            def call(*, _server=server_name, _tool=raw_name, _client=client, **kwargs):
                policy = HOST_POLICY.get((_server, _tool), "confirm")
                if policy == "deny":
                    return "MCP error: host policy denied this tool"
                if policy == "confirm" and (_server, _tool) not in _APPROVED:
                    return "MCP error: host approval required for this tool"
                return _client.call_tool(_tool, kwargs)
            handlers[name] = call
    return tools, handlers


CONNECT_MCP_TOOL = {"type": "function", "function": {
    "name": "connect_mcp", "description": "Connect a built-in mock MCP server (docs or deploy).",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"}},
                   "required": ["name"], "additionalProperties": False}}}


def assemble_tool_pool(base_tools: list[dict], base_handlers: dict):
    tools = [*base_tools, CONNECT_MCP_TOOL]
    handlers = {**base_handlers, "connect_mcp": connect_mcp}
    return _assemble(tools, handlers, _CONNECTED)
