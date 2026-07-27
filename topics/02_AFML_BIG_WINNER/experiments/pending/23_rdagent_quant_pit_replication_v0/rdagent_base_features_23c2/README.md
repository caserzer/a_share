# EP23 corrected RD-Agent base feature library

RD-Agent keeps its built-in Alpha20 Qlib-expression library. The two Python
files in this directory are loaded as static base factors:

- `close_momentum_20d.py`
- `volume_surprise_20d.py`

Do not add `base_factors.json` here. RD-Agent validates that file against its
default provider before the EP23 provider overlay is applied, which can cause a
false validation failure. Omitting it intentionally preserves the already
validated built-in Alpha20 expressions.

The static implementations are required because Qlib `Ref` uses calendar
displacement, while the agent-generated implementations use per-instrument
observed-row displacement. They are not interchangeable around missing or
suspended sessions.
