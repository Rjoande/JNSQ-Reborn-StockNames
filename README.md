# JNSQ-Reborn-StockNames

ModuleManager patch that gives the celestial bodies of [JNSQ-Reborn](https://github.com/rbeap/JNSQ-Reborn) their stock internal names back (`Kerbin` instead of `JNSQKerbin`, `Mun` instead of `JNSQMun`, and so on for all 31 bodies), so that the rest of the KSP ecosystem keeps working with it.

## Why

JNSQ-Reborn deletes every body of classic JNSQ and recreates it with an internal name prefixed by `JNSQ`. The display name is unchanged, but the internal name is what the game and every other mod key on. As a consequence, with plain JNSQ-Reborn:

- science result texts fall back to the generic ones: stock `ScienceDefs`, Bluedog, Tantares, CrowdSourcedScience and any custom science pack are keyed on `KerbinSrfLanded...`, `MunInSpaceLow...`;
- Contract Configurator packs with `targetBody = Kerbin` (Anomaly Surveyor, Tourism, Field Research, ...) fail to load those contracts;
- Kerbal Konstructs statics from other packs and the ones you place yourself on `Kerbin` are not loaded;
- NavInstruments runways, SpaceDust resource bands, Strategia body strategies and icons (JNSQ-Reborn issue #4), Waypoint Manager's KSC waypoint (issue #5), Final Frontier ribbons and everything else that stores a body name stop matching;
- existing JNSQ save games cannot be continued.

Reading JNSQ-Reborn's configs, the only technical effect of the prefix is to shield its bodies from patches written for the stock names that run in later ModuleManager passes (the Parallax stock texture packs, for example). JNSQ-Reborn already does that explicitly in `Configs/KillStock.cfg`, and the `:FINAL` pass of ModuleManager makes it possible to keep that isolation *while patching* and still hand the game the stock names *at runtime*. That is what this patch does.

## What it does

Three generated files in `GameData/JNSQ-Reborn-StockNames/`:

| File | Pass | Purpose |
|---|---|---|
| `01_StockNames.cfg` | `:FINAL` | Renames the 31 bodies and every JNSQ-Reborn config that refers to them: Kopernicus bodies and orbits, asteroid spawn locations, home world, EVE clouds/shadows/PQS/wet surfaces/city lights, Scatterer atmospheres, oceans and planet list (eclipse casters, secondary suns, light sources), Parallax terrain and scatters, Kerbal Konstructs instances, group centers and map decals, NavInstruments runways, MechJeb sites, Distant Object, PlanetShine, Firefly, Kerbalism, Rational Resources / CRP, Deployed Science, CommNet Constellation, ROC definitions, contract settings, ResearchBodies. |
| `00_DedupeLeftovers.cfg` | `:FINAL`, applied first | JNSQ-Reborn requires classic JNSQ to stay installed and relies on its stock-named configs (EVE eclipses, Scatterer atmospheres, Kerbal Konstructs sites, MechJeb sites, ...) pointing at bodies that no longer exist. With the stock names back they would load twice. This file removes them while the Reborn copies still carry their `JNSQ*` names (ModuleManager applies `:FINAL` patches in file order and the rename comes next), so only the leftovers match; leftovers added by late passes of other mods, such as patch-style Scatterer configs, are caught too. Kerbal Konstructs statics are removed only for the 27 site groups shipped by classic JNSQ and for the stock-Kerbin bases shipped by Kerbin Side Remastered and Ordinary Konstruction Co (JNSQ-Reborn uses their models and re-places what it needs); the `Ungrouped` group, where your own statics go, is never touched. |
| `02_Fixes.cfg` | `:AFTER[JNSQ-Reborn]` | Re-applies JNSQ-Reborn's own `initialRotation += 180` for Kerbin (sunrise at the KSC at 06:00), which its `Configs/OffsetTime.cfg` tries to apply in `:AFTER[JNSQ]`, a pass that runs before the Reborn bodies exist. Delete this file if you do not want it. |

Because the rename happens in `:FINAL`, every JNSQ-Reborn patch, including the ones that run in `:AFTER[Kopernicus]`, `:AFTER[ParallaxStock]` and `:LAST[scattererJNSQ]`, still sees `JNSQKerbin` and behaves exactly as designed. Only the database the game reads carries the stock names.

Nothing inside `GameData/JNSQ-Reborn` is modified.

## Installation

1. Install JNSQ-Reborn and its dependencies as described in its README (classic JNSQ stays installed).
2. Copy `GameData/JNSQ-Reborn-StockNames` into your `GameData`.
3. Delete `GameData/ScattererAtmosphereCache` if it exists: the cache is keyed on the atmosphere name.
4. Start the game. Optionally run `tools/check_cache.py` against `GameData/ModuleManager.ConfigCache` afterwards (see below).

Requirements: JNSQ-Reborn 1.0.0 or later, ModuleManager 4.2.x. No other dependency.

**Save games.** If you already have a career started on plain JNSQ-Reborn, its vessels and science subjects are stored with the `JNSQ*` names and will not survive this patch. Start a new game, or do not install it. A save started on classic JNSQ, on the other hand, keeps the stock names and can in principle be loaded; terrain has changed under landed vessels, so treat that as an experiment and keep a backup.

## Known limitations

- `Configs/ScienceParamModifier.cfg` of JNSQ-Reborn selects its entries with `JNSQ*` names in a pass that runs before this patch; with Science Param Modifier installed those adjustments will not apply.
- Rational Resources and Blueshift configs are renamed but have not been validated in a game with those mods installed.
- JNSQ-Reborn's `Configs/CommNetConstellation.cfg` and classic JNSQ's file of the same name both run in `:LAST[JNSQ]` and both delete and re-create the ground station list; the classic one is applied last and wins. This is independent from the names and is reported upstream.
- JNSQ-Reborn's Kerbal Konstructs sites use the models of Omega's Stockalike Structures, Kerbin Side Remastered, Tundra's Space Center and Ordinary Konstruction Co. Without those packs Kerbal Konstructs logs one "No Model named ..." line per missing static, with or without this patch. Kerbin Side Remastered and Ordinary Konstruction Co also ship bases placed on the stock Kerbin (`Statics/ExampleBases`, `Bases`): this patch removes those placements, and you can simply not install those folders.

## Updating for a new JNSQ-Reborn version

The three `.cfg` files are generated from the JNSQ-Reborn install, so do not edit them by hand:

```bash
python tools/generate.py --reborn <KSP>/GameData/JNSQ-Reborn --jnsq <KSP>/GameData/JNSQ --gamedata <KSP>/GameData
python tools/check_reborn.py <KSP>/GameData/JNSQ-Reborn
```

`check_reborn.py` lists every place where JNSQ-Reborn uses a `JNSQ*` body name, grouped by config context, and reports `UNKNOWN` for contexts the generator does not handle yet. After starting the game once:

```bash
python tools/check_cache.py <KSP>/GameData/ModuleManager.ConfigCache
```

reads ModuleManager's fully patched database and reports any `JNSQ*` body token left, duplicate bodies/atmospheres/EVE objects, the home world and Kerbin's rotation.

Python 3.8 or later, no third-party packages.

## License

MIT, see `LICENSE`. JNSQ-Reborn (CC-BY-NC-SA) and JNSQ are not redistributed.
