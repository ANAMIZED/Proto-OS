"""MCP adapter: server, client, mux, OpenAPI->MCP, paid tools, resource cache."""
from __future__ import annotations

from .canonical import ProtoError, new_id

ERR_PAYMENT_REQUIRED = -32002

class MCPServer:
    def __init__(self, name: str, payee_did: str | None = None):
        self.name = name
        self.payee_did = payee_did
        self.tools = {}

    def add_tool(self, name, description, schema, handler, price=0.0):
        self.tools[name] = {"description": description, "schema": schema,
                            "handler": handler, "price": price}

    def list_tools(self):
        return [{"name": n, **{k: v for k, v in t.items() if k != "handler"}} for n, t in self.tools.items()]

    def call(self, name, arguments):
        t = self.tools.get(name)
        if not t: raise ProtoError(f"unknown tool {name}")
        if t["price"] > 0:
            return {"error": {"code": ERR_PAYMENT_REQUIRED, "message": "payment required",
                              "data": {"amount": t["price"], "payee": self.payee_did}}}
        result = t["handler"](**arguments) if arguments else t["handler"]()
        return {"structuredContent": result}

class MCPMux:
    def __init__(self):
        self._servers = {}

    def mount(self, prefix, server):
        self._servers[prefix] = server

    def servers(self):
        return self._servers

    def call(self, tool, arguments, payer_did=None, budget_id=None, os_=None):
        if "." in tool:
            prefix, name = tool.split(".", 1)
        else:
            prefix, name = "", tool
        srv = self._servers.get(prefix)
        if not srv: raise ProtoError(f"unknown MCP server {prefix}")
        result = srv.call(name, arguments)
        if isinstance(result, dict) and result.get("error", {}).get("code") == ERR_PAYMENT_REQUIRED:
            if os_ and budget_id:
                # auto-pay via wallet
                amount = result["error"]["data"]["amount"]
                os_.wallet.check_budget(budget_id, amount)
                os_.wallet.budgets[budget_id].spent_total += amount
                # retry free after payment
                t = srv.tools[name]
                res = t["handler"](**arguments) if arguments else t["handler"]()
                return {"structuredContent": res}
            raise ProtoError("payment required and no budget")
        return result

class MCPClient:
    def __init__(self, mux):
        self.mux = mux
    def call(self, tool, arguments):
        return self.mux.call(tool, arguments)

class ResourceCache:
    def __init__(self, engine, audit, maxsize=128):
        self.engine, self.audit = engine, audit
        self._cache = {}
        self.maxsize = maxsize
    def get(self, key):
        return self._cache.get(key)
    def put(self, key, value):
        if len(self._cache) >= self.maxsize:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value

def openapi_to_mcp(spec, transport=None):
    # offline stub
    return MCPServer("openapi")
