---
name: kb-check
description: Deterministic gate for a card/graph knowledge base built by kb-build -- validates ids, graph edges, evidence coverage and card completeness without any LLM. Run after every kb-build; the RE pipeline fails when it fails.
license: Proprietary
metadata:
  author: ADLC KB Team
  version: "0.1.0"
  organization: AIG
  plugin: AIDLC-kb
allowed-tools: Bash Read
---

# kb-check — deterministic KB gate

Run:

```
python ${CLAUDE_PLUGIN_ROOT}/skills/kb-check/kb_check.py kb
```

Exit 0 = PASS (report printed as JSON, also written to `kb/_gate-results.json`).
Exit 1 = FAIL — the report lists each finding with the card / edge concerned. Fix
the KB (never delete evidence to make a gate pass) and re-run.

Checks: `ids` (unique, `PREFIX-APP-NNNN` shape) · `graph` (every edge endpoint is a
node; every card is a node) · `evidence` (every card has ≥1 evidence line; no orphan
evidence) · `cards` (label + summary present, kind matches prefix) · `export`
(`cards.jsonl` in sync with the card files).
