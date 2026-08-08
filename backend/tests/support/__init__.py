"""Test support. Fixtures, world builders, and the domain-API adapter.

Nothing in here is production code and nothing in here may reimplement a
business rule. `world.py` builds contract objects only; `domain_api.py` resolves
the policy callables under test without ever substituting for them
(foodflow_clean_code_spec.md 10.2).
"""
