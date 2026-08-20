"""Obsidian vault export of a ProtoOS world."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

def vault_notes(os_) -> dict[str, str]:
    notes = {}
    idents = getattr(os_.ids, "_identities", {})
    for ident in idents.values():
        notes[f"id-{ident.name}"] = f"# {ident.name}\n\ndid: `{ident.did}`\nkind: {ident.kind}\n"
    budgets = getattr(os_.wallet, "budgets", {})
    for b in budgets.values():
        notes[f"budget-{b.id[-6:]}"] = f"# Budget {b.id[-6:]}\n\nowner: [[{b.owner}]]\nlimit: {b.limit_total}\nspent: {os_.wallet.spent(b.id)}\n"
    notes["audit"] = "# Audit\n\n| seq | action |\n|-----|--------|\n" + "\n".join(
        f"| {e.get('i', e.get('seq', ''))} | {e.get('action')} |" for e in os_.audit.entries[-20:]
    )
    return notes

def unresolved_links(notes_or_dir) -> list[str]:
    if isinstance(notes_or_dir, dict):
        notes = notes_or_dir
    else:
        notes = {}
        for p in Path(notes_or_dir).rglob("*.md"):
            notes[p.stem] = p.read_text()
    link_re = re.compile(r"\[\[([^\]]+)\]\]")
    keys = set(notes)
    bad = []
    for name, body in notes.items():
        for m in link_re.finditer(body):
            target = m.group(1).split("|")[0].strip()
            if target not in keys and not any(target in k for k in keys):
                bad.append(f"{name} -> {target}")
    return bad

def write_vault(os_, dest) -> int:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    notes = vault_notes(os_)
    for name, body in notes.items():
        (dest / f"{name}.md").write_text(body)
    return len(notes)

def write_vault_zip(os_, dest) -> int:
    dest = Path(dest)
    notes = vault_notes(os_)
    with zipfile.ZipFile(dest, "w") as z:
        for name, body in notes.items():
            z.writestr(f"{name}.md", body)
    return len(notes)
