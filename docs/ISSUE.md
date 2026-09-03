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

## Two unrelated things found on the way

- `Configs/OffsetTime.cfg` applies `@initialRotation += 180` to `@Body[JNSQKerbin]` in `:AFTER[JNSQ]`. ModuleManager processes mod passes alphabetically and `JNSQ` sorts before `JNSQ-Reborn`, so `:AFTER[JNSQ]` runs before `:FOR[JNSQ-Reborn]` creates the body: the rotation offset is silently skipped (the Kronometer half of the file does apply). `:AFTER[JNSQ-Reborn]` fixes it.
- `Configs/CommNetConstellation.cfg` runs in `:LAST[JNSQ]`, the same pass as classic JNSQ's file of the same name; both delete and re-create `GroundStations`, and `JNSQ/JNSQ_Configs/...` is applied after `JNSQ-Reborn/Configs/...` within the pass, so the classic list wins. `:LAST[JNSQ-Reborn]` would fix it.

Thanks for reading, and again for the mod.
