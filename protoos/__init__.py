"""ProtoOS — Unified Autonomous Protocols Operating System (reference implementation).

Public API surface. Import from here.
"""
from .canonical import (
    BudgetExceeded, Clock, FixedClock, PolicyDenied, ProtoError, ProtoHalted,
    RateLimited, cjson, new_id,
)
from .core import OSContext, PendingApproval, ProtoOS
from .commerce import Catalog, Product
from .identity import EnterpriseIdPStub, IdentityService, default_backend
from .policy import MandateInvalid, MandateStore, PolicyEngine, Rule, safe_eval
from .registry import (
    FederatedRegistry, LocalRegistry, SemanticIndex, UnifiedAgentCard,
    WellKnownDirectory, rank_candidates,
)
from .runtime import KillSwitch, RateLimiter, SandboxedExecutor, SessionManager, TaskGraph
from .wallet import Budget, Receipt, SpendingController
from .a2a import (
    A2AAdapter, AGUIBus, HUMAN_INPUT_REQUEST, HUMAN_INPUT_RESULT,
    InputRequired, RUN_FINISHED, RUN_STARTED, STATE_DELTA, TEXT_MESSAGE,
    TOOL_CALL_END, TOOL_CALL_START,
)
from .mcp import MCPClient, MCPMux, MCPServer, ResourceCache, openapi_to_mcp
from .audit import AuditLog, Tracer
from .graph import build_graph, constellation_layout, constellation_svg, layout, to_dot, to_json, to_svg
from .vault import unresolved_links, vault_notes, write_vault, write_vault_zip

__version__ = "0.2.0"
__all__ = [
    "ProtoOS", "Catalog", "Product", "OSContext", "PendingApproval",
    "Budget", "Receipt", "SpendingController",
    "PolicyEngine", "MandateStore", "Rule", "safe_eval",
    "IdentityService", "EnterpriseIdPStub", "default_backend",
    "LocalRegistry", "FederatedRegistry", "WellKnownDirectory",
    "UnifiedAgentCard", "SemanticIndex", "rank_candidates",
    "A2AAdapter", "AGUIBus", "InputRequired",
    "MCPServer", "MCPClient", "MCPMux", "ResourceCache", "openapi_to_mcp",
    "AuditLog", "Tracer",
    "TaskGraph", "SessionManager", "RateLimiter", "KillSwitch", "SandboxedExecutor",
    "Clock", "FixedClock", "ProtoError", "PolicyDenied", "BudgetExceeded",
    "ProtoHalted", "RateLimited", "MandateInvalid",
    "build_graph", "layout", "to_json", "to_dot", "to_svg",
    "constellation_layout", "constellation_svg",
    "write_vault", "write_vault_zip", "vault_notes", "unresolved_links",
    "HUMAN_INPUT_REQUEST", "HUMAN_INPUT_RESULT", "RUN_STARTED", "RUN_FINISHED",
    "STATE_DELTA", "TEXT_MESSAGE", "TOOL_CALL_START", "TOOL_CALL_END",
    "__version__",
]
