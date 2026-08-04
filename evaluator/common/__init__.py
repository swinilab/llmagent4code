"""Checks shared by both evaluation profiles.

The prescriptive profile (prompts/generate.md) hands the agent every threshold
and every interface; the open profile (prompts/latest.md) hands it tactic
definitions and lets it choose its own mechanisms, thresholds and verification.
What survives that difference lives here: resolving a claimed function against
delivered source, validating API manifests against the running routes, and
generating the mechanical half of a boundary-value suite from a constraint
table.
"""
