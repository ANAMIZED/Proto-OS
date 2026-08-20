"""ProtoOS CLI — thin surface over the control plane.

Usage:
  python -m protoos.cli status
  python -m protoos.cli verify
  python -m protoos.cli demo
  python -m protoos.cli graph [outdir]
  python -m protoos.cli vault [path.zip]
"""
from __future__ import annotations

import argparse
import sys


def cmd_status(_: argparse.Namespace) -> int:
    from . import __version__
    from .identity import default_backend
    print(f"ProtoOS {__version__}")
    print(f"crypto backend: {default_backend().name}")
    print("surfaces: policy, identity, wallet, mcp, a2a, registry, graph, vault, httpapi")
    return 0


def cmd_verify(_: argparse.Namespace) -> int:
    from .verify import main as verify_main
    verify_main()
    return 0


def cmd_demo(_: argparse.Namespace) -> int:
    import runpy
    runpy.run_module("demo", run_name="__main__")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    from . import ProtoOS
    from .graph import build_graph, layout, to_json, to_dot, to_svg
    from pathlib import Path
    out = Path(args.outdir or "out")
    out.mkdir(parents=True, exist_ok=True)
    os_ = ProtoOS()
    u = os_.create_user("demo-user")
    os_.wallet.create_budget(u.did, 100.0)
    g = build_graph(os_)
    pos = layout(g, seed=42)
    to_json(g, out / "constellation.json")
    to_dot(g, out / "constellation.dot")
    to_svg(g, pos, out / "constellation.svg")
    print(f"wrote {out}/constellation.{{json,dot,svg}}  ({len(g['nodes'])} nodes)")
    return 0


def cmd_vault(args: argparse.Namespace) -> int:
    from . import ProtoOS
    from .vault import write_vault_zip, unresolved_links
    from pathlib import Path
    dest = Path(args.path or "vault.zip")
    os_ = ProtoOS()
    u = os_.create_user("demo-user")
    os_.wallet.create_budget(u.did, 50.0)
    write_vault_zip(os_, dest)
    bad = unresolved_links(os_)
    print(f"wrote {dest}  unresolved_links={len(bad)}")
    return 0 if not bad else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="protoos", description="ProtoOS CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("verify")
    sub.add_parser("demo")
    g = sub.add_parser("graph")
    g.add_argument("outdir", nargs="?", default="out")
    v = sub.add_parser("vault")
    v.add_argument("path", nargs="?", default="vault.zip")
    args = p.parse_args(argv)
    return {
        "status": cmd_status,
        "verify": cmd_verify,
        "demo": cmd_demo,
        "graph": cmd_graph,
        "vault": cmd_vault,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
