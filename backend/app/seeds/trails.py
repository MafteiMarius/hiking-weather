"""Seed the trail catalogue (25 curated Carpathian routes).

Run from backend/ with the venv active and the database migrated:

    python -m app.seeds.trails

Idempotent: trails are matched by slug; existing rows are left untouched.
Pass --update to also refresh existing rows from this file (needed after
data corrections).

Data provenance (reviewed 2026-07-10): start/summit coordinates and summit
elevations verified against OpenStreetMap (Overpass API); trailheads are
snapped to the real feature (cabana, village centre, cable-car base).
Distances and durations are one-way trailhead→destination estimates
(full loop for circuits), cross-checked against guidebook times — treat
them as planning figures, not GPS-surveyed values. Known source conflicts:
Vârful Turnu 1923 m (guidebooks) vs 1911 m (OSM); Omu 2505 m vs 2507 m.
Difficulty: 1 walk, 2 easy, 3 mountain hike, 4 demanding, 5 exposed/very hard.
"""
import asyncio
import sys
from typing import Any

from sqlalchemy import select

from app.db.models import Trail
from app.db.session import AsyncSessionLocal


def _point(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


# (slug, name, region, difficulty, duration_min, distance_m, gain_m,
#  start(lat,lng), summit(lat,lng) | None, summit_elev_m | None, description)
TRAILS: list[dict[str, Any]] = [
    # ── Bucegi ────────────────────────────────────────────────────────────
    dict(slug="omu-valea-jepilor", name="Vârful Omu via Valea Jepilor", region="Bucegi",
         difficulty=4, duration_minutes=360, distance_m=9000, elevation_gain_m=1620,
         start=(45.4088, 25.5253), summit=(45.4456, 25.4563), summit_elev_m=2505,
         description="Bușteni (Telecabina) – Valea Jepilor – Cabana Caraiman – Vârful Omu. Steep, sustained climb; the classic hard route out of Bușteni."),
    dict(slug="crucea-caraiman", name="Crucea Caraiman via Jepii Mici", region="Bucegi",
         difficulty=3, duration_minutes=300, distance_m=7000, elevation_gain_m=1400,
         start=(45.4088, 25.5253), summit=(45.4160, 25.4975), summit_elev_m=2291,
         description="Bușteni (Telecabina) – Jepii Mici – Crucea Caraiman. Relentless but well-marked ascent to the WWI memorial cross."),
    dict(slug="babele-sfinx-plateau", name="Babele & Sfinx plateau loop", region="Bucegi",
         difficulty=1, duration_minutes=150, distance_m=6000, elevation_gain_m=270,
         start=(45.3838, 25.4877), summit=(45.4083, 25.4702), summit_elev_m=2216,
         description="Easy plateau walk from Cabana Piatra Arsă to the Babele and Sfinx rock formations. Exposed to wind — check gusts."),
    dict(slug="omu-malaiesti", name="Vârful Omu via Valea Mălăiești", region="Bucegi",
         difficulty=4, duration_minutes=420, distance_m=12000, elevation_gain_m=1650,
         start=(45.5336, 25.4403), summit=(45.4456, 25.4563), summit_elev_m=2505,
         description="Glăjărie – Cabana Mălăiești – Hornurile Mălăiești – Omu. Snow lingers in the hornuri into June."),
    # ── Piatra Craiului ───────────────────────────────────────────────────
    dict(slug="piscul-baciului-plaiul-foii", name="Piscul Baciului (La Om) via La Lanțuri", region="Piatra Craiului",
         difficulty=5, duration_minutes=270, distance_m=5500, elevation_gain_m=1400,
         start=(45.5623, 25.1967), summit=(45.5270, 25.2117), summit_elev_m=2238,
         description="Cabana Plaiul Foii – La Lanțuri (chains) – Piscul Baciului. Exposed limestone scramble; dry weather only."),
    dict(slug="turnu-curmatura", name="Vârful Turnu via Curmătura", region="Piatra Craiului",
         difficulty=3, duration_minutes=240, distance_m=7500, elevation_gain_m=1200,
         start=(45.5607, 25.3162), summit=(45.5568, 25.2518), summit_elev_m=1923,
         description="Zărnești – Cabana Curmătura – Vârful Turnu. Northern ridge access; a good first taste of the Craiului ridge."),
    dict(slug="prapastiile-zarnestiului", name="Prăpăstiile Zărneștiului gorge", region="Piatra Craiului",
         difficulty=1, duration_minutes=150, distance_m=8000, elevation_gain_m=250,
         start=(45.5540, 25.3010), summit=None, summit_elev_m=None,
         description="Flat walk through the dramatic Zărnești gorge. Family-friendly; shaded most of the day."),
    # ── Făgăraș ───────────────────────────────────────────────────────────
    dict(slug="moldoveanu-sambata", name="Vârful Moldoveanu via Valea Sâmbetei", region="Făgăraș",
         difficulty=5, duration_minutes=420, distance_m=14000, elevation_gain_m=1900,
         start=(45.6916, 24.7995), summit=(45.5996, 24.7362), summit_elev_m=2544,
         description="Complexul Sâmbăta – Fereastra Mare – Viștea Mare – Moldoveanu. Romania's highest point; very long day, start early."),
    dict(slug="negoiu-porumbacu", name="Vârful Negoiu via Cabana Negoiu", region="Făgăraș",
         difficulty=5, duration_minutes=540, distance_m=17000, elevation_gain_m=1950,
         start=(45.7137, 24.4734), summit=(45.5850, 24.5586), summit_elev_m=2535,
         description="Porumbacu de Sus – Cabana Negoiu – Strunga Dracului (chains) – Negoiu. Second-highest peak; serious undertaking."),
    dict(slug="balea-capra", name="Bâlea Lac – Șaua Caprei – Lacul Capra", region="Făgăraș",
         difficulty=2, duration_minutes=180, distance_m=5000, elevation_gain_m=300,
         start=(45.6039, 24.6172), summit=(45.6015, 24.6234), summit_elev_m=2315,
         description="Short alpine crossing from the Transfăgărășan, out and back. Big views for little effort; crowded in August."),
    dict(slug="podragu-arpas", name="Cabana Podragu via Valea Arpașului", region="Făgăraș",
         difficulty=3, duration_minutes=420, distance_m=14000, elevation_gain_m=1500,
         start=(45.6979, 24.6110), summit=(45.6103, 24.6872), summit_elev_m=2136,
         description="Păstrăvăria Albota (Arpașu de Sus) – Cabana Podragu. Long forested approach to the highest hut in the Făgăraș; base for Moldoveanu."),
    dict(slug="urlea-breaza", name="Vârful Urlea via Valea Pojortei", region="Făgăraș",
         difficulty=4, duration_minutes=480, distance_m=13000, elevation_gain_m=1750,
         start=(45.7060, 24.8821), summit=(45.6065, 24.8299), summit_elev_m=2473,
         description="Breaza – Valea Pojortei – former Cabana Urlea – Vârful Urlea. Quieter eastern Făgăraș; glacial lake under the summit."),
    # ── Retezat ───────────────────────────────────────────────────────────
    dict(slug="peleaga-carnic", name="Vârful Peleaga via Pietrele", region="Retezat",
         difficulty=4, duration_minutes=330, distance_m=10000, elevation_gain_m=1500,
         start=(45.4340, 22.8935), summit=(45.3656, 22.8929), summit_elev_m=2509,
         description="Cârnic – Cabana Pietrele – Curmătura Bucurei – Peleaga. Retezat's highest; granite boulder fields near the top."),
    dict(slug="bucura-lake", name="Lacul Bucura via Curmătura Bucurei", region="Retezat",
         difficulty=3, duration_minutes=270, distance_m=9000, elevation_gain_m=1150,
         start=(45.4340, 22.8935), summit=(45.3604, 22.8749), summit_elev_m=2040,
         description="Cârnic – Pietrele – Lacul Bucura, Romania's largest glacial lake. Classic Retezat introduction."),
    dict(slug="retezat-peak", name="Vârful Retezat via Șaua Retezatului", region="Retezat",
         difficulty=4, duration_minutes=300, distance_m=8500, elevation_gain_m=1450,
         start=(45.4340, 22.8935), summit=(45.3808, 22.8493), summit_elev_m=2482,
         description="Cârnic – Cabana Pietrele – Valea Stânișoarei – the iconic trapezoid summit that names the massif."),
    # ── Apuseni ───────────────────────────────────────────────────────────
    dict(slug="cetatile-ponorului", name="Cetățile Ponorului from Padiș", region="Apuseni",
         difficulty=2, duration_minutes=240, distance_m=12000, elevation_gain_m=500,
         start=(46.5957, 22.7338), summit=(46.5633, 22.7015), summit_elev_m=1000,
         description="Cabana Padiș – Cetățile Ponorului karst fortress and back. Spectacular sinkholes and cave portals; sturdy shoes needed."),
    dict(slug="cucurbata-mare", name="Vârful Bihor (Cucurbăta Mare)", region="Apuseni",
         difficulty=2, duration_minutes=240, distance_m=8000, elevation_gain_m=900,
         start=(46.4762, 22.7579), summit=(46.4408, 22.6889), summit_elev_m=1849,
         description="Arieșeni – Vârful Bihor, the highest point of the Apuseni. Gentle gradients, big plateau views."),
    dict(slug="galbena-gorge", name="Cheile Galbenei circuit", region="Apuseni",
         difficulty=3, duration_minutes=330, distance_m=14000, elevation_gain_m=600,
         start=(46.5776, 22.7040), summit=None, summit_elev_m=None,
         description="Glăvoi (Padiș) – Poiana Florilor – Cheile Galbenei with cables and ladders through the gorge. Slippery when wet."),
    # ── Ceahlău ───────────────────────────────────────────────────────────
    dict(slug="toaca-durau", name="Vârful Toaca via Cabana Fântânele", region="Ceahlău",
         difficulty=3, duration_minutes=240, distance_m=6500, elevation_gain_m=1100,
         start=(46.9949, 25.9247), summit=(46.9775, 25.9499), summit_elev_m=1904,
         description="Durău – Fântânele – Toaca. Stairs to the summit cone; the classic Ceahlău ascent."),
    dict(slug="ocolasul-mare", name="Ocolașul Mare via Izvorul Muntelui", region="Ceahlău",
         difficulty=3, duration_minutes=240, distance_m=7500, elevation_gain_m=1100,
         start=(46.9543, 25.9889), summit=(46.9527, 25.9467), summit_elev_m=1907,
         description="Cabana Izvorul Muntelui – Curmătura Lutu Roșu – Dochia plateau. Ceahlău's true high point sits in a reserve — viewed from the plateau."),
    # ── Ciucaș ────────────────────────────────────────────────────────────
    dict(slug="ciucas-peak", name="Vârful Ciucaș via Muntele Roșu", region="Ciucaș",
         difficulty=3, duration_minutes=240, distance_m=8000, elevation_gain_m=1100,
         start=(45.4600, 25.9380), summit=(45.5217, 25.9265), summit_elev_m=1954,
         description="Cheia – Muntele Roșu – Vârful Ciucaș. Conglomerate towers and mushroom rocks; photogenic at sunrise."),
    dict(slug="tigaile-mari", name="Tigăile Mari circuit", region="Ciucaș",
         difficulty=3, duration_minutes=270, distance_m=9000, elevation_gain_m=900,
         start=(45.4600, 25.9380), summit=None, summit_elev_m=None,
         description="Loop under the Tigăile Mari towers from Cheia. Shorter alternative when the summit is in cloud."),
    # ── Iezer-Păpușa ──────────────────────────────────────────────────────
    dict(slug="iezerul-mare", name="Vârful Iezerul Mare via Cabana Voina", region="Iezer-Păpușa",
         difficulty=4, duration_minutes=300, distance_m=9000, elevation_gain_m=1500,
         start=(45.4417, 25.0446), summit=(45.4660, 24.9543), summit_elev_m=2462,
         description="Cabana Voina – Refugiul Iezer – Vârful Iezerul Mare. Quiet massif with Făgăraș views and few crowds."),
    dict(slug="papusa-voina", name="Vârful Păpușa via Culmea Bătrâna", region="Iezer-Păpușa",
         difficulty=4, duration_minutes=330, distance_m=11000, elevation_gain_m=1450,
         start=(45.4417, 25.0446), summit=(45.5050, 25.0612), summit_elev_m=2391,
         description="Cabana Voina – Culmea Bătrâna – Păpușa. Long grassy ridge walking; navigation is hard in fog."),
    # ── Bucegi (extra) ────────────────────────────────────────────────────
    dict(slug="jepii-mari", name="Jepii Mari – Piatra Arsă", region="Bucegi",
         difficulty=3, duration_minutes=240, distance_m=7000, elevation_gain_m=1100,
         start=(45.4088, 25.5253), summit=(45.3838, 25.4877), summit_elev_m=1950,
         description="Bușteni (Telecabina) – Jepii Mari – Cabana Piatra Arsă. Gentler sibling of Jepii Mici; descend by cable car from Babele."),
]

assert len(TRAILS) == 25, f"expected 25 trails, found {len(TRAILS)}"


def _values(t: dict[str, Any]) -> dict[str, Any]:
    start_lat, start_lng = t["start"]
    summit = t["summit"]
    return dict(
        name=t["name"],
        region=t["region"],
        difficulty=t["difficulty"],
        duration_minutes=t["duration_minutes"],
        distance_m=t["distance_m"],
        elevation_gain_m=t["elevation_gain_m"],
        start_point=_point(start_lat, start_lng),
        summit_point=_point(*summit) if summit else None,
        summit_elev_m=t["summit_elev_m"],
        description=t["description"],
    )


async def seed_trails(session, *, update: bool = False) -> int:
    """Insert any trails whose slug is missing. Returns number created.

    With update=True, existing rows are also refreshed from TRAILS —
    needed to propagate data corrections, since the default mode
    deliberately never touches rows already in the database.
    """
    existing = {
        t.slug: t
        for t in (await session.execute(select(Trail))).scalars()
    }
    created = 0
    for t in TRAILS:
        row = existing.get(t["slug"])
        if row is None:
            session.add(Trail(slug=t["slug"], **_values(t)))
            created += 1
        elif update:
            for field, value in _values(t).items():
                setattr(row, field, value)
    await session.commit()
    return created


def main() -> None:
    update = "--update" in sys.argv[1:]

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            created = await seed_trails(session, update=update)
            rest = len(TRAILS) - created
            print(f"Trails seeded: {created} created, {rest} "
                  + ("refreshed" if update else "already present"))

    asyncio.run(run())


if __name__ == "__main__":
    main()
