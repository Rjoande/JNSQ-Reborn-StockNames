# Changelog

## 1.0.0 - 2026-09-03

- First release, generated against JNSQ-Reborn v1.0.0 (31 prefixed bodies).
- `00_DedupeLeftovers.cfg`: removal of the classic-JNSQ / stock EVE / Firefly / Scatterer configs that would otherwise load twice (`:FINAL`, applied first).
- `01_StockNames.cfg`: rename of bodies and of every JNSQ-Reborn config keyed on them (`:FINAL`).
- `02_Fixes.cfg`: re-applies the Kerbin `initialRotation` offset that JNSQ-Reborn's `OffsetTime.cfg` schedules in a pass that runs too early.
- Tools: `generate.py`, `check_reborn.py`, `check_cache.py`.
