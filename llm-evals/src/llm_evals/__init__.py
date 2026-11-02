"""llm_evals: an evaluation harness and CI release gate for LLM structured extraction.

The example task is invoice extraction. The input is the plain text of an invoice
email. The output is JSON that must match the `Invoice` schema. The harness scores
the output against a golden dataset and decides whether a release can go ahead.
"""

__version__ = "1.0.0"
