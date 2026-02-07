# Run from repo root
.PHONY: eval_policy eval_retrieval eval

eval_policy:
	python scripts/eval_policy.py

eval_retrieval:
	python scripts/eval_retrieval.py

eval: eval_policy eval_retrieval
