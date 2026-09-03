#!/usr/bin/env python3
"""List every place where a JNSQ-Reborn install uses a JNSQ-prefixed body name,
grouped by config context, and flag contexts the generator does not handle.

Usage:
    python tools/check_reborn.py <GameData/JNSQ-Reborn>

Run it after updating JNSQ-Reborn: any context marked "UNKNOWN" needs a new
template in tools/generate.py (and a new positive check here).
"""
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import parse_file  # noqa: E402

TOKEN = re.compile(r"JNSQ[A-Z][a-z]+")
ALLOW = {"JNSQReborn", "JNSQTag"}

# (regex on "path :: key") -> handled by which generated clause
KNOWN = [
    (r"Kopernicus.*/Body :: name$", "Kopernicus @Body[] @name"),
    (r"Kopernicus.*/Body :: cacheFile$", "path, not a name (ignored)"),
    (r"Kopernicus.*/Body/Orbit :: referenceBody$", "Kopernicus @Orbit @referenceBody"),
    (r"Kopernicus.*/Asteroid/Locations/(Flyby|Around)/Body :: body$", "Kopernicus @Asteroid Locations"),
    (r"Kopernicus_config :: %?HomeWorldName$", "Kopernicus_config HomeWorldName"),
    (r"Kopernicus.*/@Body\[JNSQ\*\]", "patch selector applied before :FINAL (ignored)"),
    (r"EVE_CLOUDS/OBJECT :: body$", "EVE_CLOUDS"),
    (r"EVE_SHADOWS/OBJECT :: (body|caster)$", "EVE_SHADOWS"),
    (r"PQS_MANAGER/OBJECT :: body$", "PQS_MANAGER"),
    (r"EVE_WET_SURFACES_CONFIG/OBJECT :: body$", "EVE_WET_SURFACES_CONFIG"),
    (r"EVE_CITY_LIGHTS.*:: @body$", "EVE_CITY_LIGHTS"),
    (r"Scatterer_atmosphere.*/Atmo :: name$", "Scatterer_atmosphere"),
    (r"Scatterer_ocean/Ocean :: name$", "Scatterer_ocean"),
    (r"Scatterer_planetsList.*/Item :: (celestialBodyName|transformName)$", "Scatterer_planetsList Item"),
    (r"Scatterer_planetsList.*/Item/eclipseCasters :: Item$", "Scatterer_planetsList eclipseCasters"),
    (r"Scatterer_planetsList.*/Item/secondarySuns/Item :: celestialBodyName$", "Scatterer_planetsList secondarySuns"),
    (r"Scatterer_planetsList.*/celestialLightSourcesData/Item :: bodyName$", "Scatterer_planetsList light sources"),
    (r"Scatterer_planetsList.*/!Item", "deletion of classic entries (ignored)"),
    (r"ParallaxTerrain/Body :: name$", "ParallaxTerrain"),
    (r"ParallaxScatters/Body :: name$", "ParallaxScatters"),
    (r"ParallaxTerrain.*/@Body\[JNSQ\*\]", "patch selector applied before :FINAL (ignored)"),
    (r"STATIC/Instances :: CelestialBody$", "KK STATIC Instances"),
    (r"KK_GroupCenter :: CelestialBody$", "KK_GroupCenter"),
    (r"KK_MapDecal :: CelestialBody$", "KK_MapDecal"),
    (r"MechJeb2Landing/LandingSites/Site :: body$", "MechJeb sites"),
    (r"MechJeb2Landing/Runways/Runway :: body$", "MechJeb runways"),
    (r"Runway.* :: body$", "NavInstruments Runway"),
    (r"CelestialBodyColor.* :: name$", "DistantObject"),
    (r"PlanetshineCelestialBody.* :: name$", "PlanetShine"),
    (r"ATMOFX_BODY.* :: name$", "Firefly"),
    (r"RadiationBody :: name$", "Kerbalism"),
    (r"(PLANETARY|BIOME)_RESOURCE.* :: @?PlanetName$", "PLANETARY_RESOURCE / BIOME_RESOURCE"),
    (r"DEPLOYEDSCIENCE.*/ENTRY :: BodyName$", "DEPLOYEDSCIENCE"),
    (r"CommNetConstellationSettings.*/GroundStation :: CustomCelestialBody$", "CommNetConstellation"),
    (r"ROC_DEFINITION/CELESTIALBODY :: Name$", "ROC_DEFINITION"),
    (r"RESOURCE_REQUEST.* :: Forbidden$", "Contracts ISRU Forbidden"),
    (r"RESEARCHBODIES/ONDISCOVERY :: <JNSQ\*> =$", "ResearchBodies ONDISCOVERY"),
    (r"RESEARCHBODIES/IGNORELEVELS :: <JNSQ\*> =$", "ResearchBodies IGNORELEVELS"),
    (r"RESEARCHBODIES/IGNORE :: body$", "ResearchBodies IGNORE"),
    (r"ScienceParamModifier|ScienceConfigValuesNode", "ScienceParamModifier selectors (known limitation, see README)"),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    root = sys.argv[1]
    agg = OrderedDict()
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if not f.lower().endswith(".cfg"):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            grp = rel
            if rel.startswith("Configs/KK/") and not rel.endswith(("DefaultColor.cfg", "NavUltRunways.cfg")):
                grp = "Configs/KK/<sites>"
            elif rel.startswith("Bodies/Rescale/"):
                grp = "Bodies/Rescale/<body>"
            elif rel.startswith("Bodies/"):
                grp = "Bodies/<body>"
            elif "/Planets/" in rel or rel.startswith(("Configs/Firefly/", "Configs/Parallax/Scatters/")):
                grp = rel.rsplit("/", 1)[0] + "/<body>"
            tree = parse_file(full)

            def walk(node, path):
                for k, v in node.values:
                    hits = [t for t in TOKEN.findall(v) if t not in ALLOW]
                    khits = [t for t in TOKEN.findall(k) if t not in ALLOW]
                    if hits or khits:
                        key = (grp, path, k if not khits else "<JNSQ*> =")
                        agg[key] = agg.get(key, 0) + 1
                for c in node.children:
                    walk(c, (path + "/" if path else "") + TOKEN.sub("JNSQ*", c.header))
            walk(tree, "")
    unknown = 0
    for (g, path, k), n in agg.items():
        sig = f"{path} :: {k}"
        label = next((lab for rx, lab in KNOWN if re.search(rx, sig)), None)
        if label is None:
            unknown += 1
            label = "UNKNOWN"
        # patches inside Rescale/ and Bodies/Rescale/ run in :AFTER[JNSQ-Reborn], before :FINAL
        if g.startswith(("Rescale/", "Bodies/Rescale/")) and label == "UNKNOWN":
            label = "selector in a pre-:FINAL patch (ignored)"
            unknown -= 1
        print(f"{n:5d}  {label:52s}  {g}  {sig}")
    print(f"\n{'UNKNOWN contexts: %d' % unknown if unknown else 'all contexts known'}")
    sys.exit(1 if unknown else 0)


if __name__ == "__main__":
    main()
