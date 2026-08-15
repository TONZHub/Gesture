"""Barnaby: the agent layer.

Layout:
    acts.py      the five acts and what cognitive demand each one names
    guard.py     the banned-phrase contract, enforced on every line of output
    voice.py     the local voice engine — always available, never calls out
    barnaby.py   the Strands agent, with voice.py as its fallback
    rhythm.py    when to check in, and how much to ask for
    patterns.py  correlations, surfaced only when honest and only when useful
    sky.py       the week rendered as light
"""
