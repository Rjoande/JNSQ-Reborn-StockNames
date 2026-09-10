# Release text (GitHub release / forum post)

Recommended sequence, based on how the two existing issues went (#4 "Strategia uses JNSQ(Body) names" was closed as completed with "i doubt this is something i can fix as i believe strategia grabs the internal names"; #5 on Waypoint Manager is open without a reply):

1. Publish the standalone patch first (this release text), so the fix exists whatever happens upstream.
2. Open the upstream issue (`docs/ISSUE.md`) linking to it, offering a PR. Done 2026-09-11: https://github.com/rbeap/JNSQ-Reborn/issues/7. A bare PR that renames 3,460 lines is unlikely to be merged without that conversation, because it would break the careers of current Reborn users; the issue lets the author decide between a major version, an optional variant, or endorsing the external patch.

---

## GitHub release: JNSQ-Reborn-StockNames 1.0.1

**Stock internal body names for JNSQ-Reborn.**

JNSQ-Reborn recreates every body as `JNSQKerbin`, `JNSQMun`, ... The display names are the same, but the internal names are what science definitions, contract packs, Kerbal Konstructs, NavInstruments, SpaceDust, Strategia, Waypoint Manager, Final Frontier and your save games are keyed on, so all of those stop matching.

This patch renames the bodies, and every JNSQ-Reborn config that refers to them, back to `Kerbin`, `Mun`, ... in ModuleManager's `:FINAL` pass, after all of JNSQ-Reborn's own patches have run. JNSQ-Reborn is not modified and behaves exactly as designed while it is being applied; only the database the game reads carries the stock names.

What you get back: science texts (stock and modded), Contract Configurator packs, Kerbal Konstructs statics on Kerbin, NavInstruments runways, SpaceDust bands, Strategia strategies and icons (JNSQ-Reborn #4), the Waypoint Manager KSC waypoint (#5), Final Frontier ribbons, and the possibility to load a career started on classic JNSQ (experimental, keep a backup).

**Install**: drop `GameData/JNSQ-Reborn-StockNames` into `GameData`, delete `GameData/ScattererAtmosphereCache` if present, start the game. Requires JNSQ-Reborn 1.0.0+ (with classic JNSQ, as JNSQ-Reborn requires) and ModuleManager 4.2.x.

**Warning**: a career already started on plain JNSQ-Reborn stores the `JNSQ*` names and will not survive this patch. Start a new game or skip the patch.

**Also included** (`02_Fixes.cfg`, delete it if unwanted): re-applies JNSQ-Reborn's own "sunrise at KSC at 06:00" rotation offset, which its `OffsetTime.cfg` schedules in a pass that runs before the Reborn bodies exist.

**Known limitations**: see the README (Science Param Modifier, Rational Resources / Blueshift not validated, CommNet Constellation list overridden by classic JNSQ upstream, KK models from OSSNTR / KSR / TSC / OKC still required for JNSQ-Reborn's sites).

Verified on KSP 1.12.5 with JNSQ-Reborn 1.0.0, Kopernicus 1.12.1-247, Parallax Continued 1.0.x, EVE volumetrics (Jan 2026 build), Scatterer 0.0903: after a full load, ModuleManager's ConfigCache contains no `JNSQ*` body token, one Kopernicus body per stock name, one Scatterer atmosphere per body, no duplicate EVE object.

The three `.cfg` files are generated (`tools/generate.py`); `tools/check_reborn.py` flags config contexts a new JNSQ-Reborn version might introduce, `tools/check_cache.py` validates the result against the ConfigCache. MIT.

---

## Forum post (short)

**[1.12.x] JNSQ-Reborn-StockNames 1.0.1**: a ModuleManager patch that gives JNSQ-Reborn's bodies their stock internal names back (`Kerbin` instead of `JNSQKerbin`). With plain JNSQ-Reborn, everything keyed on internal body names silently stops matching: science result texts (stock and modded), Contract Configurator packs, Kerbal Konstructs statics, NavInstruments, SpaceDust, Strategia, Waypoint Manager, Final Frontier, saves. The patch runs in `:FINAL`, after JNSQ-Reborn's own patches, so JNSQ-Reborn itself is untouched and behaves as designed; only the final database carries the stock names. Do not install it on a career already started on JNSQ-Reborn. Download, README and tools: https://github.com/Rjoande/JNSQ-Reborn-StockNames (release: https://github.com/Rjoande/JNSQ-Reborn-StockNames/releases/tag/v1.0.1). Upstream discussion: https://github.com/rbeap/JNSQ-Reborn/issues/7.
