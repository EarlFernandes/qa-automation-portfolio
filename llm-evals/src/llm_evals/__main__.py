"""Allow `python -m llm_evals ...` as an alternative to the `llm-evals` script."""

from llm_evals.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
