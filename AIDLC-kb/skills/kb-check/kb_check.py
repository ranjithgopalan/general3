#!/usr/bin/env python
"""Deterministic gate for a card/graph KB (layout: see fe_core.kb.cards).

    python kb_check.py <kb_root> [--json]

Exit 0 on PASS, 1 on FAIL. Pure standard library so it runs inside a Claude Code
session that has no project venv on its PATH.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ID_RE = re.compile(r"^[A-Z]{2,6}(?:-[A-Z0-9]{1,24}){1,5}$")
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


def _front_matter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            else:
                v = v.strip("'\"")
            meta[k.strip()] = v
    return meta


def check(root: Path) -> dict:
    findings: list[dict] = []
    cards: dict[str, dict] = {}
    knowledge = root / "knowledge"
    for path in sorted(knowledge.rglob("*.md")) if knowledge.is_dir() else []:
        meta = _front_matter(path.read_text(encoding="utf-8", errors="replace"))
        cid = str(meta.get("id") or "").strip()
        if not cid:
            continue
        if cid in cards:
            findings.append({"check": "ids", "id": cid, "msg": f"duplicate id (also {cards[cid]['path']})"})
        if not ID_RE.match(cid):
            findings.append({"check": "ids", "id": cid, "msg": "malformed id (PREFIX-APP-NNNN expected)"})
        kind = str(meta.get("kind") or "")
        if kind and cid.split("-", 1)[0] != kind.upper():
            findings.append({"check": "cards", "id": cid, "msg": f"kind {kind!r} does not match id prefix"})
        if not meta.get("label"):
            findings.append({"check": "cards", "id": cid, "msg": "missing label"})
        if not meta.get("summary"):
            findings.append({"check": "cards", "id": cid, "msg": "missing summary"})
        cards[cid] = {"path": str(path.relative_to(root)), "kind": kind}

    # graph
    nodes: set[str] = set()
    edges = 0
    gpath = knowledge / "ontology" / "graph.json"
    if gpath.is_file():
        try:
            g = json.loads(gpath.read_text(encoding="utf-8"))
        except ValueError as exc:
            findings.append({"check": "graph", "msg": f"graph.json unreadable: {exc}"})
            g = {}
        nodes = {str(n.get("id")) for n in g.get("nodes", []) if n.get("id")}
        for e in g.get("edges", []):
            edges += 1
            for end in (e.get("source"), e.get("target")):
                if end not in nodes:
                    findings.append({"check": "graph", "id": str(end), "msg": "edge endpoint is not a node"})
        for cid in cards:
            if cid not in nodes:
                findings.append({"check": "graph", "id": cid, "msg": "card has no graph node"})
    else:
        findings.append({"check": "graph", "msg": "knowledge/ontology/graph.json missing"})

    # evidence
    ev_count: Counter = Counter()
    epath = root / "evidence" / "evidence-map.jsonl"
    if epath.is_file():
        for i, line in enumerate(epath.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                findings.append({"check": "evidence", "msg": f"line {i}: not JSON"})
                continue
            cid = str(d.get("id") or d.get("card_id") or "")
            if cid not in cards:
                findings.append({"check": "evidence", "id": cid, "msg": f"line {i}: evidence for unknown card"})
            if not d.get("locus") or not d.get("source_doc"):
                findings.append({"check": "evidence", "id": cid, "msg": f"line {i}: missing source_doc/locus"})
            ev_count[cid] += 1
        for cid in cards:
            if ev_count[cid] == 0:
                findings.append({"check": "evidence", "id": cid, "msg": "card has no evidence"})
    else:
        findings.append({"check": "evidence", "msg": "evidence/evidence-map.jsonl missing"})

    # export
    xpath = root / "cards.jsonl"
    if xpath.is_file():
        exported = set()
        for line in xpath.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                exported.add(str(json.loads(line).get("id")))
            except ValueError:
                pass
        missing = sorted(set(cards) - exported)
        extra = sorted(exported - set(cards))
        if missing:
            findings.append({"check": "export", "msg": f"cards.jsonl lacks {len(missing)} card(s): {missing[:5]}"})
        if extra:
            findings.append({"check": "export", "msg": f"cards.jsonl has {len(extra)} unknown id(s): {extra[:5]}"})
    else:
        findings.append({"check": "export", "msg": "cards.jsonl missing"})

    by_kind = Counter(cid.split("-", 1)[0] for cid in cards)
    return {
        "root": str(root), "pass": not findings,
        "cards": len(cards), "nodes": len(nodes), "edges": edges,
        "evidence": sum(ev_count.values()), "kinds": dict(by_kind),
        "findings": findings,
    }


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    root = Path(argv[0])
    report = check(root)
    try:
        (root / "_gate-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
