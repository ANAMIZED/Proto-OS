"""ProtoOS — Unified Autonomous Protocols Operating System (reference impl).

Compose, don't replace: MCP, A2A, AP2, x402, MPP, UCP-style commerce, AG-UI,
ANP/DID-style identity — behind one policy-governed control plane.
"""
from .a2a import (A2AAdapter, AGUIBus, InputRequired, RUN_FINISHED, RUN_STARTED,
                  HUMAN_INPUT_REQUEST, HUMAN_INPUT_RESULT, STATE_DELTA,
                  TEXT_MESSAGE, TOOL_CALL_END, TOOL_CALL_START)
from .audit import AuditLog, Tracer
from .canonical import (BudgetExceeded, Clock, MandateInvalid,
                        PolicyDenied, ProtoError, ProtoHalted, RateLimited)
from .commerce import Catalog
from .core import OSContext, PendingApproval, ProtoOS
from .identity import IdentityService, default_backend
from .mcp import MCPClient, MCPMux, MCPServer, ResourceCache
from .policy import MandateStore, PolicyEngine, safe_eval
from .registry import (FederatedRegistry, LocalRegistry, SemanticIndex,
                       UnifiedAgentCard, WellKnownDirectory, rank_candidates)
from .runtime import (KillSwitch, RateLimiter, SandboxedExecutor, SessionManager,
                      TaskGraph)
from .wallet import Budget, Receipt, SpendingController
from .graph import build_graph, layout as constellation_layout, to_svg as constellation_svg
from .vault import vault_notes, write_vault, write_vault_zip

# Optional / reconstructed aliases for compatibility
try:
    from .canonical import FixedClock
except ImportError:
    FixedClock = Clock
try:
    from .commerce import Product
except ImportError:
    Product = None
try:
    from .policy import Rule
except ImportError:
    Rule = None
try:
    from .mcp import openapi_to_mcp
except ImportError:
    def openapi_to_mcp(*a, **k): return MCPServer("openapi")
try:
    from .identity import EnterpriseIdPStub
except ImportError:
    EnterpriseIdPStub = None

__version__ = "0.2.0"
__all__ = [
    "ProtoOS", "OSContext", "PendingApproval", "Clock", "FixedClock",
    "ProtoError", "PolicyDenied", "ProtoHalted", "RateLimited", "BudgetExceeded",
    "MandateInvalid", "IdentityService", "EnterpriseIdPStub", "default_backend",
    "AuditLog", "Tracer", "PolicyEngine", "MandateStore", "Rule", "safe_eval",
    "UnifiedAgentCard", "LocalRegistry", "WellKnownDirectory", "FederatedRegistry",
    "SemanticIndex", "rank_candidates", "SpendingController", "Budget", "Receipt",
    "MCPServer", "MCPClient", "MCPMux", "openapi_to_mcp", "ResourceCache",
    "A2AAdapter", "AGUIBus", "InputRequired", "Catalog", "Product",
    "RateLimiter", "KillSwitch", "SandboxedExecutor", "TaskGraph", "SessionManager",
    "build_graph", "constellation_layout", "constellation_svg",
    "vault_notes", "write_vault", "write_vault_zip",
]
