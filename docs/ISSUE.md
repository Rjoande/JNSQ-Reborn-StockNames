# Proposed upstream issue for rbeap/JNSQ-Reborn

Suggested title: **Internal body names are prefixed (JNSQKerbin, JNSQMun, ...): this breaks every mod and save keyed on body names. Proposal + ready-made patch**

---

First of all, thank you for Reborn. The Parallax integration on all 31 bodies, the volumetric weather and the Mitchell-Netravali height maps are a real step up from classic JNSQ, and the work is clearly systematic.

I would like to raise one design decision that has a much larger blast radius than it looks: the bodies are created with the internal name prefixed by `JNSQ` (`Bodies/*.cfg`: `name = JNSQKerbin`, `Configs/KopernicusSettings.cfg` deletes the classic bodies, `Configs/Homeworld.cfg` sets `HomeWorldName = JNSQKerbin`). The display name is untouched, but the internal name is the key that KSP and every other mod use.

## What stops working with the prefix

Verified on a KSP 1.12.5 install with Reborn 1.0.0, by reading the configs and ModuleManager's ConfigCache:

- **Science result texts.** Subject ids are built from `body.name`, so `KerbinSrfLandedKSC` becomes `JNSQKerbinSrfLandedKSC`. Every `EXPERIMENT_DEFINITION` result keyed on a body (stock `ScienceDefs.cfg`, Bluedog, Tantares, CrowdSourcedScience, any custom science pack) falls back to the generic text. On my install that is about 31,000 result lines.
- **Contract Configurator packs** with `targetBody = Kerbin` / `Mun` / `Duna` (Anomaly Surveyor, Tourism Overhaul, Field Research, ...): the contract fails to load.
- **Kerbal Konstructs**: statics from other packs and statics the player places on `Kerbin` are skipped ("body not found").
- **NavInstruments** runways, **SpaceDust** resource bands (`body = Kerbin`), **Final Frontier** ribbons, **Waypoint Manager** body icons and KSC waypoint (#5), **Strategia** body strategies and icons (#4: Strategia is not doing anything wrong, it reads `body.name`), MechJeb landing sites from other mods, and so on.
- **Save games** started on classic JNSQ cannot be continued (vessel orbits, science subjects, contracts).

## Why I think the prefix is not needed

The only technical effect of the prefix I could find is isolation: patches written for the stock names that run in later ModuleManager passes (for example the Parallax stock texture packs, `:FOR[ParallaxStock]` and `:AFTER[Kopernicus]`) cannot touch Reborn's bodies. But Reborn already does that isolation explicitly and completely in `Configs/KillStock.cfg` (removes the Parallax PQS mods and the `ParallaxTerrain`/`ParallaxScatters` bodies for the stock names). Classic JNSQ itself used `!Body[Kerbin]` + `Body { name = Kerbin }` in its own pass for years without problems.

Everything else the prefix touched was cost, not benefit: 2447 `CelestialBody` lines in the KK configs, the NavInstruments runways, MechJeb sites, Distant Object, PlanetShine, `Homeworld.cfg`, the explicit deletion of the classic Scatterer/EVE entries by name, and issues #4 and #5.

## Options

1. **Drop the prefix upstream.** Mechanical search-and-replace (about 3,460 occurrences, all in configs, no plugin involved), plus removing `Homeworld.cfg`. `KillStock.cfg` keeps the isolation. Cost: careers already started on Reborn 1.0 would need a restart, which argues for doing it in a major version.
2. **Keep the config names, rename at the end.** Kopernicus supports `cbNameLater` (present in the current Kopernicus.dll), which lets a body be configured under one name and exposed to the game under another. Every Reborn config that stores the name would still have to be rewritten, so this is not cheaper than option 1.
3. **External patch** (what I did while waiting): https://github.com/rjoande/JNSQ-Reborn-StockNames. Three generated ModuleManager files that run in `:FINAL`, after every Reborn patch, and rename the bodies and every Reborn config keyed on them back to the stock names, plus a dedupe of the classic-JNSQ leftovers that come back to life once the stock names exist. Reborn's own patching is unchanged (it still sees `JNSQKerbin` while it runs); only the database the game reads carries the stock names. It comes with a generator and a checker that reads the ConfigCache and reports any prefixed token left, so it can be regenerated for each Reborn release. I am happy to turn it into a PR in whatever form you prefer, or to keep maintaining it as an optional add-on if you would rather not change the names.

## Three unrelated things found on the way

- `Configs/OffsetTime.cfg` applies `@initialRotation += 180` to `@Body[JNSQKerbin]` in `:AFTER[JNSQ]`. ModuleManager processes mod passes alphabetically and `JNSQ` sorts before `JNSQ-Reborn`, so `:AFTER[JNSQ]` runs before `:FOR[JNSQ-Reborn]` creates the body: the rotation offset is silently skipped (the Kronometer half of the file does apply). `:AFTER[JNSQ-Reborn]` fixes it.
- `Configs/CommNetConstellation.cfg` runs in `:LAST[JNSQ]`, the same pass as classic JNSQ's file of the same name; both delete and re-create `GroundStations`, and `JNSQ/JNSQ_Configs/...` is applied after `JNSQ-Reborn/Configs/...` within the pass, so the classic list wins. `:LAST[JNSQ-Reborn]` would fix it.
- Kerbin's coasts glow white/pink at low sun in flight (not in map view). Two things add up: `Configs/Parallax/Terrain.cfg` keeps the stock Parallax sand band (`_LowMidBlendStart/End` 30/60 m) and the stock broad specular (`_SpecularPower 5`, `_FresnelPower 0.8`), and on JNSQ's flat coastal plains that paints hundreds of metres of bright sand along every shore; `Configs/Scatterer/Planets/Oceans.cfg` gives Kerbin `transparencyDepth = 100` (classic JNSQ: 10) and `shoreFoam = 1`, so the sandy seabed and the foam make a bright band on the sea side too. On my install a `:FINAL` patch with `_LowMidBlendStart/End` 3/10, `_SpecularIntensity` 0.06, `_FresnelPower` 3, `transparencyDepth` 25 and `shoreFoam` 0.3 removes the glow; the exact values are a matter of taste, the direction is what matters.

Thanks for reading, and again for the mod.

---

## Follow-up comment posted 2026-09-11 (phantom NavInstruments runways)

https://github.com/rbeap/JNSQ-Reborn/issues/7#issuecomment-5626639880

One more thing found on the way, about NavInstruments (NavUtilities Continued) ILS runways. Reborn's `Configs/KK/NavUltRunways.cfg` covers every runway of the new bases (thanks for that, both ends each), but with the packs Reborn requires, the loaded runway list also contains entries for bases that do not exist on Reborn's Kerbin:

- **54 runways at stock-Kerbin coordinates.** NavInstruments ships `ModuleManagerCfgs/KerbinSideRemastered.cfg`, gated on `:NEEDS[KerbinSideRemastered]`. Since Reborn needs the KSR folder for its models, that file loads and adds Baikerbanur, Cape Kerman, Kojave Sands, Kerman Atoll, etc. at their stock positions, which on JNSQ fall in the open sea or in the middle of nowhere. Same logic for the Ordinary Konstruction "Island" airfield and Tundra Space Center: `ModuleManagerCfgs/JNSQ.cfg` has `Island ILS 09/27` (1.5° S, 71.9° W) and `TSC ILS 09/27` (13.6° S, 51.6° E) with no base there under Reborn.
- **KSC 09/27 twice.** NavInstruments' `JNSQ.cfg` (still active, classic JNSQ being required) has `KSC ILS 09/27` and Reborn adds `KSC 09/27`. Measured against the runway (91°50'47" W to 91°46'06" W at 0°01'04" N), the NavInstruments pair puts the glideslope touchdown before the threshold (32 m short on 09, 263 m short on 27) while Reborn's pair lands on the runway (255 m and 22 m past the threshold), so Reborn's entries are the ones to keep; the 27 touchdown might deserve another ~250 m.
- `Xennone Nat'l Lab 03` has no `21` counterpart, while the KK launch site is "Runway 21".

Since Reborn already owns a NavInstruments file and requires those packs, it could carry the cleanup itself. What I use, in `:FINAL` (spaces in `:HAS` values must be `?`):

```
!Runway:HAS[#ident[Baikerbanur*]]:NEEDS[NavInstruments]:FINAL {}
!Runway:HAS[#ident[Cape?Kerman*]]:NEEDS[NavInstruments]:FINAL {}
// ... one line per KSR base prefix (Desert?Airfield, Dununda, Harvester, Hazard, Jeb?s?Junkyard,
// Kamberwick, Kerman?Atoll, Kermundsen, Kojave?Sands, Kola?Island, Meeda, Nye, Polar, Round,
// Sandy?Island, South?Field, South?Lake, TSC, Ubderdam, Uberdam, XXX) ...
!Runway:HAS[#ident[Island?ILS*]]:NEEDS[NavInstruments]:FINAL {}
!Runway:HAS[#ident[KSC?ILS*]]:NEEDS[NavInstruments]:FINAL {}
```

With that, the ConfigCache goes from 221 `Runway` nodes to 161, all of them on bases that exist. Not related to the naming question, just reporting it while I have the numbers at hand.
