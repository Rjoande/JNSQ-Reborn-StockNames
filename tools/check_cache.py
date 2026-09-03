#!/usr/bin/env python3
"""Verify the result of the patch against ModuleManager's ConfigCache.

Usage:
    python tools/check_cache.py <KSP>/GameData/ModuleManager.ConfigCache

Run KSP once (to the main menu is enough) after installing JNSQ-Reborn and
JNSQ-Reborn-StockNames, then point this script at the ConfigCache. It is the
ground truth: the fully patched database the game actually loaded.

Reports:
  * every remaining "JNSQ<Body>" token (there should be none),
  * a few positive checks: one Kopernicus body per stock name, no duplicate
    Scatterer atmospheres / EVE objects per body, home world, Kerbin rotation.
"""
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfglib import parse  # noqa: E402

TOKEN = re.compile(r"JNSQ[A-Z][a-z]+")
ALLOW = {"JNSQReborn", "JNSQTag"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    print(f"cache: {path} ({len(text) / 1e6:.1f} MB)")

    # 1. leftover tokens, with the UrlConfig they live in
    leftovers = Counter()
    where = defaultdict(Counter)
    current = "?"
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("name = ") and current == "UrlConfig?":
            current = s[7:]
            continue
        if s == "UrlConfig":
            current = "UrlConfig?"
            continue
        if "JNSQ" not in s or s.startswith("//"):
            continue
        for mt in TOKEN.finditer(s):
            tok = mt.group(0)
            if tok in ALLOW:
                continue
            before = s[mt.start() - 1:mt.start()]
            after = s[mt.end():mt.end() + 1]
            if before in ("/", "_") or after in ("/", "_", "."):
                continue  # file path or texture name, not a body reference
            leftovers[tok] += 1
            where[tok][current] += 1
    if leftovers:
        print(f"\nLEFTOVER JNSQ-prefixed tokens: {sum(leftovers.values())}")
        for tok, n in leftovers.most_common():
            print(f"  {tok}: {n}")
            for cfg, k in where[tok].most_common(5):
                print(f"      {k:5d}  in {cfg}")
    else:
        print("\nno JNSQ-prefixed body token left in the database: OK")

    # 2. positive checks on the parsed tree
    root = parse(text)
    bodies = Counter()
    home = None
    kerbin_rot = None
    atmos = Counter()
    oceans = Counter()
    atmo_other = Counter()
    ocean_other = Counter()
    reborn_bodies = set()
    n_atmo_nodes = 0
    eve_objects = Counter()
    kk_instances = Counter()
    scat_items = Counter()
    for uc in root.nodes("UrlConfig"):
        for node in uc.children:
            k = node.kind
            if k == "Kopernicus":
                for b in node.nodes("Body"):
                    bodies[b.get("name")] += 1
                    if b.get("JNSQRebornTag"):
                        reborn_bodies.add(b.get("name"))
                    if b.get("name") == "Kerbin":
                        for pr in b.nodes("Properties"):
                            kerbin_rot = pr.get("initialRotation")
            elif k == "Kopernicus_config":
                home = node.get("HomeWorldName")
            elif k == "Scatterer_atmosphere":
                n_atmo_nodes += 1
                for a in node.nodes("Atmo"):
                    atmos[a.get("name")] += 1
                    if not a.get("JNSQRebornTag"):
                        atmo_other[a.get("name")] += 1
            elif k == "Scatterer_ocean":
                for a in node.nodes("Ocean"):
                    oceans[a.get("name")] += 1
                    if not a.get("JNSQRebornTag"):
                        ocean_other[a.get("name")] += 1
            elif k == "Scatterer_planetsList":
                for lst in node.nodes("scattererCelestialBodies"):
                    for it in lst.nodes("Item"):
                        scat_items[it.get("celestialBodyName")] += 1
            elif k in ("EVE_CLOUDS", "EVE_SHADOWS", "PQS_MANAGER", "EVE_WET_SURFACES_CONFIG", "EVE_CITY_LIGHTS"):
                for o in node.nodes("OBJECT"):
                    eve_objects[(k, o.get("body"), o.get("name"))] += 1
            elif k == "STATIC":
                for inst in node.nodes("Instances"):
                    kk_instances[inst.get("CelestialBody")] += 1

    def dup(counter, label):
        d = {n: c for n, c in counter.items() if c > 1}
        print(f"  {label}: {len(counter)} distinct, duplicates: {d if d else 'none'}")

    print("\nKopernicus bodies:", " ".join(sorted(n for n in bodies if n)))
    dup(bodies, "Kopernicus Body nodes per name")
    print(f"  HomeWorldName = {home}")
    print(f"  Kerbin initialRotation = {kerbin_rot}")
    print(f"  JNSQ-Reborn bodies (JNSQRebornTag): {len(reborn_bodies)}")
    print(f"  Scatterer_atmosphere nodes: {n_atmo_nodes} (patch-style configs, JNSQ-Reborn included, add their Atmo to every node, so {n_atmo_nodes} copies per name are normal)")
    la = {n: c for n, c in atmo_other.items() if n in reborn_bodies}
    lo = {n: c for n, c in ocean_other.items() if n in reborn_bodies}
    print(f"  Scatterer Atmo of a Reborn body NOT coming from JNSQ-Reborn (leftovers): {la or None}")
    print(f"  Scatterer Ocean of a Reborn body NOT coming from JNSQ-Reborn (leftovers): {lo or None}")
    print(f"  Scatterer Atmo names: {len(atmos)}, Ocean names: {len(oceans)}")
    dup(scat_items, "Scatterer planetsList items per body")
    print(f"  EVE objects with duplicate (type, body, name): "
          f"{ {k: v for k, v in eve_objects.items() if v > 1} or 'none'}")
    print("  KK instances per body:", dict(kk_instances))
    sys.exit(1 if (leftovers or la or lo) else 0)


if __name__ == "__main__":
    main()
