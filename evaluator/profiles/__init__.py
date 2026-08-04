"""Evaluation profiles.

Two prompts ask for the same system in different ways, and they cannot share a
scoring rule:

  prescriptive  prompts/generate.md fixes the tactics, the interfaces, the
                fault-injection hooks and every numeric threshold. The
                evaluator injects the faults itself and compares measurements
                against thresholds.yaml, which is transcribed from the prompt.

  open          prompts/latest.md gives tactic definitions from
                Bass/Clements/Kazman and leaves the mechanisms, thresholds and
                verification approach to the agent. The evaluator cannot supply
                thresholds it never specified, so instead it audits the
                verification suite the agent was required to deliver.

Keeping them apart matters for what may be claimed. A prescriptive PASS says a
mechanism behaved as specified under an externally injected fault. An open PASS
says the agent built a mechanism, verified it credibly, and its own evidence
survived independent auditing -- a weaker claim about behaviour and a stronger
one about design.
"""
