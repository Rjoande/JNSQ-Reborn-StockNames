#!/usr/bin/env python3
"""Generate the JNSQ-Reborn-StockNames ModuleManager patches.

Usage:
    python tools/generate.py --reborn <GameData/JNSQ-Reborn> [--jnsq <GameData/JNSQ>] [--out <folder>]

JNSQ-Reborn creates every celestial body with an internal name prefixed by
"JNSQ" (JNSQKerbin, JNSQMun, ...). Everything in the KSP ecosystem that is keyed
on the internal body name (science definitions, contract packs, Kerbal
Konstructs packs, saves, NavInstruments, SpaceDust, Strategia icons, ...) stops
matching. This generator reads a JNSQ-Reborn install and writes patches that
run in the :FINAL pass, after every JNSQ-Reborn patch has been applied, and
rename the bodies (and every config that refers to them) back to the stock
names. At runtime the game sees "Kerbin", while JNSQ-Reborn's own patching,
which happens earlier, keeps working on "JNSQKerbin".

The generator is data-driven where the data cannot be derived from the body
list alone (eclipse casters, shadow casters, ResearchBodies texts, ...) and
template-driven elsewhere. Re-run it whenever JNSQ-Reborn is updated, then run
tools/check_reborn.py to be told about config contexts it does not know yet.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import parse_file  # noqa: E402

PREFIX = "JNSQ"
NEEDS = "NEEDS[JNSQ-Reborn]"

# Kerbal Konstructs groups shipped by classic JNSQ 0.10.x (JNSQ/JNSQ_Configs/KK).
# Used as a fallback when --jnsq is not given. JNSQ-Reborn re-ships all of them.
JNSQ_CLASSIC_KK_GROUPS = [
    "ALeonov", "AirBaseBoneyard", "AirBaseN32A", "AirBaseN46A", "AirBaseN76A",
    "AirBaseS00A", "AirBaseS05A", "AirBaseS24A", "AirBaseS28A", "AirBaseS37A",
    "AirBaseS72A", "CMcAuliffe", "CYeager", "CYeagerHarbor", "Darude",
    "DarudeHarbor", "KSCHarbor", "McMurdo", "ObservatoryNorth",
    "ObservatorySouth", "SMusgrave", "VTereshkova", "Welcome", "WelcomeHarbor",
    "Woomera2", "YGagarin", "vonKermanTri",
]


def walk_cfgs(root):
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            if f.lower().endswith(".cfg"):
                yield os.path.join(dp, f)


class Emitter:
    def __init__(self):
        self.lines = []
        self.depth = 0

    def line(self, s=""):
        self.lines.append(("\t" * self.depth + s) if s else "")

    def open(self, header):
        self.line(header)
        self.line("{")
        self.depth += 1

    def close(self):
        self.depth -= 1
        self.line("}")

    def text(self):
        return "\n".join(self.lines) + "\n"


def is_prefixed(name):
    return bool(name) and name.startswith(PREFIX) and name[len(PREFIX):len(PREFIX) + 1].isupper() \
        and name[len(PREFIX) + 1:len(PREFIX) + 2].islower()


def collect(reborn, jnsq):
    d = {}
    bodies = {}   # JNSQKerbin -> Kerbin
    ref = {}      # JNSQMun -> referenceBody (raw)
    bodies_dir = os.path.join(reborn, "Bodies")
    for path in sorted(os.listdir(bodies_dir)):
        full = os.path.join(bodies_dir, path)
        if not path.lower().endswith(".cfg") or not os.path.isfile(full):
            continue
        for body in parse_file(full).find("Body"):
            name = body.get("name")
            if is_prefixed(name):
                bodies[name] = name[len(PREFIX):]
                orbit = body.nodes("Orbit")
                if orbit and orbit[0].get("referenceBody"):
                    ref[name] = orbit[0].get("referenceBody")
    d["bodies"] = bodies
    d["ref"] = ref
    prefixed = set(bodies)

    def m(v):
        if v in bodies:
            return bodies[v]
        return v[len(PREFIX):] if is_prefixed(v) else v

    d["map"] = m

    # EVE shadows: body + repeated 'caster' values
    shadows = []
    p = os.path.join(reborn, "Configs", "EVE", "Shadows.cfg")
    if os.path.isfile(p):
        for obj in parse_file(p).find("OBJECT"):
            b = obj.get("body")
            if b in prefixed:
                shadows.append((b, obj.getall("caster")))
    d["shadows"] = shadows

    # Scatterer planets list
    items = []
    lights = []
    p = os.path.join(reborn, "Configs", "Scatterer", "PlanetsList.cfg")
    if os.path.isfile(p):
        tree = parse_file(p)
        for top in tree.find("Scatterer_planetsList"):
            for lst in top.nodes("scattererCelestialBodies"):
                for it in lst.nodes("Item"):
                    if it.header != "Item":
                        continue  # skip "!Item:HAS[...]" deletions
                    cb = it.get("celestialBodyName")
                    if cb not in prefixed:
                        continue
                    casters = []
                    for ec in it.nodes("eclipseCasters"):
                        casters = ec.getall("Item")
                    suns = []
                    for ss in it.nodes("secondarySuns"):
                        suns = [x.get("celestialBodyName") for x in ss.nodes("Item")
                                if x.get("celestialBodyName") in prefixed]
                    items.append({
                        "name": cb,
                        "transform": it.get("transformName"),
                        "casters": casters if any(c in prefixed for c in casters) else None,
                        "suns": suns,
                    })
            for ld in top.nodes("celestialLightSourcesData"):
                for it in ld.nodes("Item"):
                    if it.get("bodyName") in prefixed:
                        lights.append(it.get("bodyName"))
    d["scatterer_items"] = items
    d["scatterer_lights"] = lights

    # ResearchBodies
    rb = {"name": None, "ondiscovery": [], "ignore": [], "ignorelevels": []}
    p = os.path.join(reborn, "Configs", "ResearchBodies.cfg")
    if os.path.isfile(p):
        for top in parse_file(p).find("RESEARCHBODIES"):
            if top.header != "RESEARCHBODIES":
                continue
            rb["name"] = top.get("name")
            for n in top.nodes("ONDISCOVERY"):
                rb["ondiscovery"] = [k for k, _v in n.values if is_prefixed(k)]
            for n in top.nodes("IGNORE"):
                rb["ignore"] = n.getall("body")
            for n in top.nodes("IGNORELEVELS"):
                rb["ignorelevels"] = [k for k, _v in n.values if is_prefixed(k)]
    d["researchbodies"] = rb

    # Firefly / Kerbalism bodies defined by Reborn (needed for the dedupe patch)
    ff = []
    fdir = os.path.join(reborn, "Configs", "Firefly")
    if os.path.isdir(fdir):
        for path in walk_cfgs(fdir):
            for n in parse_file(path).find("ATMOFX_BODY"):
                if n.get("name") in prefixed:
                    ff.append(n.get("name"))
    d["firefly"] = sorted(set(ff))
    kb = []
    p = os.path.join(reborn, "Configs", "Kerbalism.cfg")
    if os.path.isfile(p):
        for n in parse_file(p).find("RadiationBody"):
            if n.get("name") in prefixed:
                kb.append(n.get("name"))
    d["kerbalism"] = sorted(set(kb))

    # Contract ISRU "Forbidden"
    forb = []
    p = os.path.join(reborn, "Configs", "ContractSettings.cfg")
    if os.path.isfile(p):
        for n in parse_file(p).find("RESOURCE_REQUEST"):
            forb += [v for v in n.getall("Forbidden") if v in prefixed]
    d["forbidden"] = forb

    # classic JNSQ Kerbal Konstructs groups (for the dedupe patch)
    groups = []
    if jnsq and os.path.isdir(os.path.join(jnsq, "JNSQ_Configs", "KK")):
        for path in walk_cfgs(os.path.join(jnsq, "JNSQ_Configs", "KK")):
            for n in parse_file(path).find("KK_GroupCenter", "KK_MapDecal", "Instances"):
                g = n.get("Group")
                if g:
                    groups.append(g)
        groups = sorted(set(groups))
    if not groups:
        groups = list(JNSQ_CLASSIC_KK_GROUPS)
    d["kk_groups"] = groups
    return d


HEADER = """// {title}
// Generated by tools/generate.py of JNSQ-Reborn-StockNames. Do not edit by hand:
// re-run the generator against your JNSQ-Reborn install instead.
//
// Source: JNSQ-Reborn with {nb} prefixed bodies.
"""


def gen_stocknames(d):
    e = Emitter()
    bodies = d["bodies"]
    m = d["map"]
    e.lines.append(HEADER.format(
        title="Rename JNSQ-Reborn bodies back to the stock internal names (:FINAL pass).",
        nb=len(bodies)).rstrip("\n"))
    e.line("// Runs in :FINAL, i.e. after every JNSQ-Reborn patch (:FOR/:AFTER/:FINAL,")
    e.line("// :AFTER[Kopernicus], :AFTER[ParallaxStock], :LAST[scattererJNSQ] ...). While patching,")
    e.line("// the bodies keep their JNSQ* names, so JNSQ-Reborn's own patches and its isolation")
    e.line("// from stock-named configs are unaffected; only the final database, the one the game")
    e.line("// reads, carries the stock names.")
    e.line()

    # Kopernicus
    e.open(f"@Kopernicus:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.open(f"@Body[{j}]")
        e.line(f"@name = {s}")
        r = d["ref"].get(j)
        if r in bodies:
            e.open("@Orbit")
            e.line(f"@referenceBody = {m(r)}")
            e.close()
        e.close()
    e.line("// asteroid spawn locations (Configs/Asteroids.cfg)")
    e.open("@Asteroid,*")
    e.open("@Locations")
    for kind in ("Flyby", "Around"):
        e.open(f"@{kind}")
        for j, s in bodies.items():
            e.open(f"@Body:HAS[#body[{j}]],*")
            e.line(f"@body = {s}")
            e.close()
        e.close()
    e.close()
    e.close()
    e.close()
    e.open(f"@Kopernicus_config:{NEEDS}:FINAL")
    e.line("// JNSQ-Reborn/Configs/Homeworld.cfg sets it to JNSQKerbin")
    e.line("@HomeWorldName = Kerbin")
    e.close()
    e.line()

    # EVE
    for top in ("EVE_CLOUDS", "PQS_MANAGER", "EVE_WET_SURFACES_CONFIG", "EVE_CITY_LIGHTS"):
        e.open(f"@{top}:{NEEDS}:FINAL")
        for j, s in bodies.items():
            e.open(f"@OBJECT:HAS[#body[{j}]],*")
            e.line(f"@body = {s}")
            e.close()
        e.close()
    e.open(f"@EVE_SHADOWS:{NEEDS}:FINAL")
    seen = set()
    for j, casters in d["shadows"]:
        e.open(f"@OBJECT:HAS[#body[{j}]],*")
        e.line(f"@body = {m(j)}")
        if casters:
            e.line("!caster,* = del")
            for c in casters:
                e.line(f"caster = {m(c)}")
        e.close()
        seen.add(j)
    for j, s in bodies.items():
        if j not in seen:
            e.open(f"@OBJECT:HAS[#body[{j}]],*")
            e.line(f"@body = {s}")
            e.close()
    e.close()
    e.line()

    # Scatterer
    e.open(f"@Scatterer_atmosphere:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.open(f"@Atmo[{j}]")
        e.line(f"@name = {s}")
        e.close()
    e.close()
    e.open(f"@Scatterer_ocean:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.open(f"@Ocean[{j}]")
        e.line(f"@name = {s}")
        e.close()
    e.close()
    e.open(f"@Scatterer_planetsList:{NEEDS}:FINAL")
    e.open("@scattererCelestialBodies")
    done = set()
    for it in d["scatterer_items"]:
        j = it["name"]
        e.open(f"@Item:HAS[#celestialBodyName[{j}]],*")
        e.line(f"@celestialBodyName = {m(j)}")
        if it["transform"] is not None:
            e.line(f"@transformName = {m(it['transform'])}")
        if it["casters"]:
            e.open("@eclipseCasters")
            e.line("!Item,* = del")
            for c in it["casters"]:
                e.line(f"Item = {m(c)}")
            e.close()
        if it["suns"]:
            e.open("@secondarySuns")
            for sn in it["suns"]:
                e.open(f"@Item:HAS[#celestialBodyName[{sn}]],*")
                e.line(f"@celestialBodyName = {m(sn)}")
                e.close()
            e.close()
        e.close()
        done.add(j)
    for j, s in bodies.items():
        if j not in done:
            e.open(f"@Item:HAS[#celestialBodyName[{j}]],*")
            e.line(f"@celestialBodyName = {s}")
            e.line(f"@transformName = {s}")
            e.close()
    e.close()
    if d["scatterer_lights"]:
        e.open("@celestialLightSourcesData")
        for j in d["scatterer_lights"]:
            e.open(f"@Item:HAS[#bodyName[{j}]],*")
            e.line(f"@bodyName = {m(j)}")
            e.close()
        e.close()
    e.close()
    e.line()

    # Parallax Continued
    for top in ("ParallaxTerrain", "ParallaxScatters"):
        e.open(f"@{top}:{NEEDS}:FINAL")
        for j, s in bodies.items():
            e.open(f"@Body[{j}]")
            e.line(f"@name = {s}")
            e.close()
        e.close()
    e.line()

    # Kerbal Konstructs / NavInstruments / MechJeb
    e.open(f"@STATIC:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.open(f"@Instances:HAS[#CelestialBody[{j}]],*")
        e.line(f"@CelestialBody = {s}")
        e.close()
    e.close()
    for top in ("KK_GroupCenter", "KK_MapDecal"):
        for j, s in bodies.items():
            e.open(f"@{top}:HAS[#CelestialBody[{j}]]:{NEEDS}:FINAL")
            e.line(f"@CelestialBody = {s}")
            e.close()
    for j, s in bodies.items():
        e.open(f"@Runway:HAS[#body[{j}]]:NEEDS[NavInstruments,JNSQ-Reborn]:FINAL")
        e.line(f"@body = {s}")
        e.close()
    e.open(f"@MechJeb2Landing:{NEEDS}:FINAL")
    e.open("@LandingSites")
    for j, s in bodies.items():
        e.open(f"@Site:HAS[#body[{j}]],*")
        e.line(f"@body = {s}")
        e.close()
    e.close()
    e.open("@Runways")
    for j, s in bodies.items():
        e.open(f"@Runway:HAS[#body[{j}]],*")
        e.line(f"@body = {s}")
        e.close()
    e.close()
    e.close()
    e.line()

    # one-node-per-body configs
    for top, needs in (("CelestialBodyColor", "DistantObject,JNSQ-Reborn"),
                       ("PlanetshineCelestialBody", "PlanetShine,JNSQ-Reborn"),
                       ("ATMOFX_BODY", "Firefly,JNSQ-Reborn"),
                       ("RadiationBody", "Kerbalism,JNSQ-Reborn")):
        for j, s in bodies.items():
            e.open(f"@{top}[{j}]:NEEDS[{needs}]:FINAL")
            e.line(f"@name = {s}")
            e.close()
    for top in ("PLANETARY_RESOURCE", "BIOME_RESOURCE"):
        for j, s in bodies.items():
            e.open(f"@{top}:HAS[#PlanetName[{j}]]:{NEEDS}:FINAL")
            e.line(f"@PlanetName = {s}")
            e.close()
    e.line()

    # nested configs
    e.open("@DEPLOYEDSCIENCE:NEEDS[SquadExpansion/Serenity,JNSQ-Reborn]:FINAL")
    e.open("@SEISMICENERGY")
    for j, s in bodies.items():
        e.open(f"@ENTRY:HAS[#BodyName[{j}]],*")
        e.line(f"@BodyName = {s}")
        e.close()
    e.close()
    e.close()
    e.open("@CommNetConstellationSettings:NEEDS[CommNetConstellation,JNSQ-Reborn]:FINAL")
    e.open("@GroundStations")
    for j, s in bodies.items():
        e.open(f"@GroundStation:HAS[#CustomCelestialBody[{j}]],*")
        e.line(f"@CustomCelestialBody = {s}")
        e.close()
    e.close()
    e.close()
    e.open(f"@ROC_DEFINITION:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.open(f"@CELESTIALBODY:HAS[#Name[{j}]],*")
        e.line(f"@Name = {s}")
        e.close()
    e.close()
    if d["forbidden"]:
        e.open(f"@Contracts:{NEEDS}:FINAL")
        e.open("@ISRU")
        e.open("@RESOURCE_REQUEST:HAS[#Name[Ore]]")
        for v in d["forbidden"]:
            e.line(f"@Forbidden = {m(v)}")
        e.close()
        e.close()
        e.close()
    rb = d["researchbodies"]
    if rb["name"]:
        e.open(f"@RESEARCHBODIES:HAS[#name[{rb['name']}]]:NEEDS[ResearchBodies,JNSQ-Reborn]:FINAL")
        for node, keys in (("ONDISCOVERY", rb["ondiscovery"]), ("IGNORELEVELS", rb["ignorelevels"])):
            if keys:
                e.open(f"@{node}")
                for k in keys:
                    e.line(f"{m(k)} = #${k}$")
                    e.line(f"!{k} = del")
                e.close()
        if rb["ignore"]:
            e.open("@IGNORE")
            e.line("!body,* = del")
            for b in rb["ignore"]:
                e.line(f"body = {m(b)}")
            e.close()
        e.close()
    return e.text()


def gen_dedupe(d):
    e = Emitter()
    bodies = d["bodies"]
    e.lines.append(HEADER.format(
        title="Remove stock-named leftovers that JNSQ-Reborn replaces (:FINAL pass, applied before the rename).",
        nb=len(bodies)).rstrip("\n"))
    e.line("// JNSQ-Reborn requires classic JNSQ to stay installed and relies on the fact that")
    e.line("// its stock-named configs (EVE eclipses, Scatterer atmospheres, Kerbal Konstructs")
    e.line("// sites, MechJeb sites, ...) as well as the stock EVE/Firefly ones point at bodies")
    e.line("// that no longer exist. Once the stock names come back those configs would load")
    e.line("// twice (classic + Reborn). This file deletes them while the Reborn copies still")
    e.line("// carry their JNSQ* names, so only the leftovers match. The result is exactly the")
    e.line("// set of configs a plain JNSQ-Reborn install ends up with.")
    e.line("//")
    e.line("// It runs in :FINAL, right before 01_StockNames.cfg (ModuleManager applies :FINAL")
    e.line("// patches in file order), so leftovers added by the late passes of other mods")
    e.line("// (:LAST[...], patch-style Scatterer configs, ...) are caught as well.")
    e.line()
    for top in ("EVE_CLOUDS", "EVE_SHADOWS", "PQS_MANAGER", "EVE_WET_SURFACES_CONFIG", "EVE_CITY_LIGHTS"):
        e.open(f"@{top}:{NEEDS}:FINAL")
        for j, s in bodies.items():
            e.line(f"!OBJECT:HAS[#body[{s}]],* {{}}")
        e.close()
    e.open(f"@Scatterer_atmosphere:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.line(f"!Atmo[{s}] {{}}")
    e.close()
    e.open(f"@Scatterer_ocean:{NEEDS}:FINAL")
    for j, s in bodies.items():
        e.line(f"!Ocean[{s}] {{}}")
    e.close()
    e.open(f"@Scatterer_planetsList:{NEEDS}:FINAL")
    e.open("@scattererCelestialBodies")
    for j, s in bodies.items():
        e.line(f"!Item:HAS[#celestialBodyName[{s}]],* {{}}")
    e.close()
    e.close()
    e.line()
    e.line("// Kerbal Konstructs: only the site groups shipped by classic JNSQ, so that statics")
    e.line("// placed by the player (or by other packs) on Kerbin are left alone.")
    e.open(f"@STATIC:{NEEDS}:FINAL")
    for g in d["kk_groups"]:
        e.line(f"!Instances:HAS[#CelestialBody[Kerbin],#Group[{g}]],* {{}}")
    e.close()
    for top in ("KK_GroupCenter", "KK_MapDecal"):
        for g in d["kk_groups"]:
            e.line(f"!{top}:HAS[#CelestialBody[Kerbin],#Group[{g}]]:{NEEDS}:FINAL {{}}")
    e.line()
    e.line("// MechJeb landing sites/runways shipped by classic JNSQ (JNSQ/JNSQ_Configs/MechJeb2.cfg)")
    e.line(f"!MechJeb2Landing:HAS[@LandingSites:HAS[@Site:HAS[#name[KSC?Pad],#body[Kerbin]]]]:{NEEDS}:FINAL {{}}")
    e.line()
    if d["firefly"]:
        e.line("// Firefly: stock body configs superseded by JNSQ-Reborn/Configs/Firefly")
        for j in d["firefly"]:
            e.line(f"!ATMOFX_BODY[{d['map'](j)}]:NEEDS[Firefly,JNSQ-Reborn]:FINAL {{}}")
    if d["kerbalism"]:
        e.line("// Kerbalism: stock radiation bodies superseded by JNSQ-Reborn/Configs/Kerbalism.cfg")
        for j in d["kerbalism"]:
            e.line(f"!RadiationBody[{d['map'](j)}]:NEEDS[Kerbalism,JNSQ-Reborn]:FINAL {{}}")
    return e.text()


FIXES = """// Small fixes for JNSQ-Reborn that are not about body names but were found while
// building this patch. Delete this file if you do not want them.

// JNSQ-Reborn/Configs/OffsetTime.cfg carries JNSQ's "sunrise at KSC at 06:00" rotation
// offset as "@Kopernicus:AFTER[JNSQ] { @Body[JNSQKerbin] { @initialRotation += 180 } }".
// ModuleManager runs :AFTER[JNSQ] before :FOR[JNSQ-Reborn] (mod names are processed in
// alphabetical order and "JNSQ" sorts before "JNSQ-Reborn"), so at that time no body
// called JNSQKerbin exists yet and the offset is silently skipped, while the Kronometer
// half of the same file (game starts at 06:00) does apply. Re-apply it once the body exists.
@Kopernicus:NEEDS[JNSQ-Reborn]:AFTER[JNSQ-Reborn]
{
	@Body[JNSQKerbin]
	{
		@Properties
		{
			@initialRotation += 180
		}
	}
}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reborn", required=True, help="path to GameData/JNSQ-Reborn")
    ap.add_argument("--jnsq", default=None, help="path to GameData/JNSQ (classic); optional, used for the KK dedupe list")
    ap.add_argument("--out", default=None, help="output folder (default: <repo>/GameData/JNSQ-Reborn-StockNames)")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "GameData", "JNSQ-Reborn-StockNames")
    os.makedirs(out, exist_ok=True)
    d = collect(a.reborn, a.jnsq)
    files = {
        "00_DedupeLeftovers.cfg": gen_dedupe(d),
        "01_StockNames.cfg": gen_stocknames(d),
        "02_Fixes.cfg": FIXES,
    }
    for name, txt in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        print(f"wrote {name} ({txt.count(chr(10))} lines)")
    print(f"bodies: {len(d['bodies'])}: " + " ".join(d["bodies"].values()))
    print(f"shadows: {len(d['shadows'])}, scatterer items: {len(d['scatterer_items'])}, "
          f"light sources: {len(d['scatterer_lights'])}, researchbodies keys: "
          f"{len(d['researchbodies']['ondiscovery'])}/{len(d['researchbodies']['ignorelevels'])}, "
          f"firefly: {len(d['firefly'])}, kerbalism: {len(d['kerbalism'])}, kk groups: {len(d['kk_groups'])}")


if __name__ == "__main__":
    main()
