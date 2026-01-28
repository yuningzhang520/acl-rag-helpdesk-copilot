# Enterprise AI Helpdesk Copilot

## Overview
This repository is a clean scaffold for an **enterprise AI helpdesk copilot**: a RAG-enabled assistant that helps resolve IT/helpdesk requests with high signal retrieval, safe response policies, and measurable evaluation.

Key goals:
- **Accurate** answers grounded in approved knowledge sources (policies, runbooks, KB articles).
- **Safe-by-default** behavior (access control, data handling, prompt injection resistance).
- **Auditable** decisions (traceable citations, logs, evaluation artifacts).
- **Measurable** quality via a golden set and repeatable evaluation workflows.

## Architecture
Typical components (to be implemented in `src/`):
- **Ingestion**: connectors + parsers + chunking + metadata enrichment.
- **Indexing**: embeddings + vector store + optional keyword index.
- **Retrieval**: query rewriting, hybrid retrieval, reranking, filtering by ACL/tenancy.
- **Answering**: grounded generation with citations; refusal/redirect when unsafe or unknown.
- **Orchestration**: tool calling for ticket actions (create/update/route), runbook execution, and escalation.
- **Observability**: structured logs, traces, feedback capture, and evaluation reports.

Suggested flow:
1. User request → classification (intent, sensitivity, required permissions)
2. Retrieval (ACL-filtered) → rerank → context assembly
3. Generation (policy-constrained) → citations + action proposals
4. Optional tools (ticketing, directory lookup, runbooks) with approvals
5. Feedback loop → evaluation + iteration

## Safety & Governance
Enterprise baseline guidance (to be operationalized in code and docs):
- **Data handling**: never log secrets; minimize PII; redact before persistence; encrypt at rest and in transit.
- **Access control**: enforce ACLs/tenancy at retrieval time (and ideally at ingestion/indexing time).
- **Prompt-injection resistance**: treat retrieved content as untrusted; use strict system prompts and tool allowlists.
- **Least privilege**: tools require scoped credentials; sensitive actions require explicit user confirmation or policy approval.
- **Auditability**: store request/response metadata, citations, tool calls, and policy decisions (with retention policies).
- **Human-in-the-loop**: escalation paths for ambiguous, high-risk, or high-impact tasks.

## Evaluation
Use `golden_set/` to store evaluation datasets and expected outcomes.

Recommended evaluation dimensions:
- **Groundedness**: answer is supported by retrieved sources and cites them.
- **Correctness**: aligns with enterprise policy/runbook facts.
- **Safety**: avoids unsafe instructions, data exfiltration, or policy violations.
- **Usefulness**: actionable, concise, and resolves the ticket efficiently.
- **Retrieval quality**: recall@k, MRR, nDCG, reranker lift.

Suggested artifacts:
- `golden_set/cases/`: individual test cases (ticket text, user context, expected behavior)
- `golden_set/expected/`: expected answers, citations, and tool actions
- `golden_set/results/`: timestamped runs, metrics, and diffs

## Demo
Use `demo/` for:
- scripted walkthroughs (screenshots / terminal recordings),
- a minimal demo app or notebook,
- example tickets and “copilot responses”.

## How to Run
This scaffold intentionally does not assume a specific runtime yet.

Common next steps:
1. Implement core packages in `src/` (ingestion, retrieval, answering, eval).
2. Add a runtime entrypoint (CLI and/or web server).
3. Add environment management (e.g., `.env.example`) and secrets strategy.
4. Add CI workflows in `workflows/` (lint, test, eval, release).

When you add a runnable entrypoint, document:
- prerequisites (Python/Node, vector DB, credentials),
- setup commands,
- how to run the demo,
- how to run evaluation against `golden_set/`.

## Repo Structure
- `docs/`: product docs, architecture decisions, governance, threat models, runbooks.
- `golden_set/`: evaluation datasets and expected outputs for regression testing.
- `workflows/`: automation and CI/CD workflow definitions (platform-agnostic scaffold).
- `demo/`: demo scripts, sample tickets, and example UI/CLI showcase.
- `src/`: application source code (copilot core, connectors, retrieval, orchestration).

p.s. test