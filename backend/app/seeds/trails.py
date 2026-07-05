"""Seed the trail catalogue (25 curated Carpathian routes).

Run from backend/ with the venv active and the database migrated:

    python -m app.seeds.trails

Idempotent: trails are matched by slug; existing rows are left untouched.

⚠️ DATA REVIEW NEEDED: coordinates, distances, durations, and elevation
figures below are drafted from general route knowledge, NOT surveyed data.
Verify against official maps (Munții Noștri, OpenTopoMap) before relying on
them for real trips. Treat difficulty as: 1 walk, 2 easy, 3 mountain hike,
4 demanding, 5 exposed/very hard.
"""
import asyncio
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
         start=(45.4104, 25.5350), summit=(45.4453, 25.4567), summit_elev_m=2505,
         description="Bușteni – Valea Jepilor – Cabana Caraiman – Vârful Omu. Steep, sustained climb; the classic hard route out of Bușteni."),
    dict(slug="crucea-caraiman", name="Crucea Caraiman via Jepii Mici", region="Bucegi",
         difficulty=3, duration_minutes=300, distance_m=7500, elevation_gain_m=1350,
         start=(45.4104, 25.5350), summit=(45.4083, 25.4903), summit_elev_m=2291,
         description="Bușteni – Jepii Mici – Crucea Caraiman. Relentless but well-marked ascent to the WWI memorial cross."),
    dict(slug="babele-sfinx-plateau", name="Babele & Sfinx plateau loop", region="Bucegi",
         difficulty=1, duration_minutes=150, distance_m=6000, elevation_gain_m=250,
         start=(45.4009, 25.4775), summit=(45.4103, 25.4728), summit_elev_m=2206,
         description="Easy plateau walk from Piatra Arsă to the Babele and Sfinx rock formations. Exposed to wind — check gusts."),
    dict(slug="omu-malaiesti", name="Vârful Omu via Valea Mălăiești", region="Bucegi",
         difficulty=4, duration_minutes=420, distance_m=12000, elevation_gain_m=1700,
         start=(45.4930, 25.4400), summit=(45.4453, 25.4567), summit_elev_m=2505,
         description="Glăjărie – Cabana Mălăiești – Hornurile Mălăiești – Omu. Snow lingers in the hornuri into June."),
    # ── Piatra Craiului ───────────────────────────────────────────────────
    dict(slug="piscul-baciului-plaiul-foii", name="Piscul Baciului (La Om) via La Lanțuri", region="Piatra Craiului",
         difficulty=5, duration_minutes=420, distance_m=11000, elevation_gain_m=1400,
         start=(45.5580, 25.1770), summit=(45.5216, 25.2153), summit_elev_m=2238,
         description="Plaiul Foii – La Lanțuri (chains) – Piscul Baciului. Exposed limestone scramble; dry weather only."),
    dict(slug="turnu-curmatura", name="Vârful Turnu via Curmătura", region="Piatra Craiului",
         difficulty=3, duration_minutes=300, distance_m=10000, elevation_gain_m=1200,
         start=(45.5589, 25.3128), summit=(45.5563, 25.2500), summit_elev_m=1923,
         description="Zărnești – Cabana Curmătura – Vârful Turnu. Northern ridge access; a good first taste of the Craiului ridge."),
    dict(slug="prapastiile-zarnestiului", name="Prăpăstiile Zărneștiului gorge", region="Piatra Craiului",
         difficulty=1, duration_minutes=150, distance_m=8000, elevation_gain_m=250,
         start=(45.5540, 25.3010), summit=None, summit_elev_m=None,
         description="Flat walk through the dramatic Zărnești gorge. Family-friendly; shaded most of the day."),
    # ── Făgăraș ───────────────────────────────────────────────────────────
    dict(slug="moldoveanu-sambata", name="Vârful Moldoveanu via Valea Sâmbetei", region="Făgăraș",
         difficulty=5, duration_minutes=540, distance_m=16000, elevation_gain_m=1900,
         start=(45.6410, 24.7920), summit=(45.6003, 24.7369), summit_elev_m=2544,
         description="Complexul Sâmbăta – Fereastra Mare – Viștea Mare – Moldoveanu. Romania's highest point; very long day, start early."),
    dict(slug="negoiu-porumbacu", name="Vârful Negoiu via Cabana Negoiu", region="Făgăraș",
         difficulty=5, duration_minutes=540, distance_m=17000, elevation_gain_m=2000,
         start=(45.6900, 24.4600), summit=(45.5904, 24.5540), summit_elev_m=2535,
         description="Porumbacu de Sus – Cabana Negoiu – Strunga Dracului (chains) – Negoiu. Second-highest peak; serious undertaking."),
    dict(slug="balea-capra", name="Bâlea Lac – Șaua Caprei – Lacul Capra", region="Făgăraș",
         difficulty=2, duration_minutes=180, distance_m=5000, elevation_gain_m=350,
         start=(45.6039, 24.6172), summit=(45.5960, 24.6210), summit_elev_m=2315,
         description="Short alpine crossing from the Transfăgărășan. Big views for little effort; crowded in August."),
    dict(slug="podragu-arpas", name="Cabana Podragu via Valea Arpașului", region="Făgăraș",
         difficulty=3, duration_minutes=420, distance_m=14000, elevation_gain_m=1500,
         start=(45.7100, 24.6330), summit=(45.6162, 24.6740), summit_elev_m=2136,
         description="Arpașu de Sus – Cabana Podragu. Long forested approach to the highest hut in the Făgăraș; base for Moldoveanu."),
    dict(slug="urlea-breaza", name="Vârful Urlea via Cabana Urlea", region="Făgăraș",
         difficulty=4, duration_minutes=480, distance_m=15000, elevation_gain_m=1750,
         start=(45.6810, 24.9080), summit=(45.5949, 24.8672), summit_elev_m=2473,
         description="Breaza – Cabana Urlea – Vârful Urlea. Quieter eastern Făgăraș; glacial lake under the summit."),
    # ── Retezat ───────────────────────────────────────────────────────────
    dict(slug="peleaga-carnic", name="Vârful Peleaga via Pietrele", region="Retezat",
         difficulty=4, duration_minutes=480, distance_m=14000, elevation_gain_m=1500,
         start=(45.4106, 22.8931), summit=(45.3667, 22.8890), summit_elev_m=2509,
         description="Cârnic – Cabana Pietrele – Curmătura Bucurei – Peleaga. Retezat's highest; granite boulder fields near the top."),
    dict(slug="bucura-lake", name="Lacul Bucura via Curmătura Bucurei", region="Retezat",
         difficulty=3, duration_minutes=360, distance_m=12000, elevation_gain_m=1100,
         start=(45.4106, 22.8931), summit=(45.3585, 22.8755), summit_elev_m=2040,
         description="Cârnic – Pietrele – Lacul Bucura, Romania's largest glacial lake. Classic Retezat introduction."),
    dict(slug="retezat-peak", name="Vârful Retezat via Șaua Retezatului", region="Retezat",
         difficulty=4, duration_minutes=450, distance_m=13000, elevation_gain_m=1450,
         start=(45.4106, 22.8931), summit=(45.3766, 22.8195), summit_elev_m=2482,
         description="Cârnic – Cabana Pietrele – Șaua Retezatului – the iconic trapezoid summit that names the massif."),
    # ── Apuseni ───────────────────────────────────────────────────────────
    dict(slug="cetatile-ponorului", name="Cetățile Ponorului from Padiș", region="Apuseni",
         difficulty=2, duration_minutes=240, distance_m=12000, elevation_gain_m=500,
         start=(46.5589, 22.7259), summit=(46.5560, 22.7040), summit_elev_m=1000,
         description="Padiș plateau – Cetățile Ponorului karst fortress. Spectacular sinkholes and cave portals; sturdy shoes needed."),
    dict(slug="cucurbata-mare", name="Vârful Bihor (Cucurbăta Mare)", region="Apuseni",
         difficulty=2, duration_minutes=300, distance_m=14000, elevation_gain_m=800,
         start=(46.4728, 22.7550), summit=(46.4419, 22.6773), summit_elev_m=1849,
         description="Arieșeni – Vârful Bihor, the highest point of the Apuseni. Gentle gradients, big plateau views."),
    dict(slug="galbena-gorge", name="Cheile Galbenei circuit", region="Apuseni",
         difficulty=3, duration_minutes=330, distance_m=14000, elevation_gain_m=600,
         start=(46.5589, 22.7259), summit=None, summit_elev_m=None,
         description="Padiș – Poiana Florilor – Cheile Galbenei with cables and ladders through the gorge. Slippery when wet."),
    # ── Ceahlău ───────────────────────────────────────────────────────────
    dict(slug="toaca-durau", name="Vârful Toaca via Cabana Fântânele", region="Ceahlău",
         difficulty=3, duration_minutes=300, distance_m=9000, elevation_gain_m=1100,
         start=(46.9885, 25.9337), summit=(46.9770, 25.9508), summit_elev_m=1904,
         description="Durău – Fântânele – Toaca. Stairs to the summit cone; the classic Ceahlău ascent."),
    dict(slug="ocolasul-mare", name="Ocolașul Mare via Izvorul Muntelui", region="Ceahlău",
         difficulty=3, duration_minutes=330, distance_m=11000, elevation_gain_m=1150,
         start=(46.9436, 26.0106), summit=(46.9578, 25.9464), summit_elev_m=1907,
         description="Izvorul Muntelui – Curmătura Lutu Roșu – Dochia plateau. Ceahlău's true high point sits in a reserve — viewed from the plateau."),
    # ── Ciucaș ────────────────────────────────────────────────────────────
    dict(slug="ciucas-peak", name="Vârful Ciucaș via Muntele Roșu", region="Ciucaș",
         difficulty=3, duration_minutes=300, distance_m=10000, elevation_gain_m=1050,
         start=(45.4488, 25.9394), summit=(45.5019, 25.9482), summit_elev_m=1954,
         description="Cheia – Muntele Roșu – Vârful Ciucaș. Conglomerate towers and mushroom rocks; photogenic at sunrise."),
    dict(slug="tigaile-mari", name="Tigăile Mari circuit", region="Ciucaș",
         difficulty=3, duration_minutes=270, distance_m=9000, elevation_gain_m=900,
         start=(45.4488, 25.9394), summit=None, summit_elev_m=None,
         description="Loop under the Tigăile Mari towers from Cheia. Shorter alternative when the summit is in cloud."),
    # ── Iezer-Păpușa ──────────────────────────────────────────────────────
    dict(slug="iezerul-mare", name="Vârful Iezerul Mare via Cabana Voina", region="Iezer-Păpușa",
         difficulty=4, duration_minutes=420, distance_m=13000, elevation_gain_m=1500,
         start=(45.3467, 24.9439), summit=(45.4880, 24.9840), summit_elev_m=2462,
         description="Voina – Lacul Iezer – Vârful Iezerul Mare. Quiet massif with Făgăraș views and few crowds."),
    dict(slug="papusa-voina", name="Vârful Păpușa via Culmea Bătrâna", region="Iezer-Păpușa",
         difficulty=4, duration_minutes=420, distance_m=14000, elevation_gain_m=1450,
         start=(45.3467, 24.9439), summit=(45.4830, 25.0210), summit_elev_m=2391,
         description="Voina – Culmea Bătrâna – Păpușa. Long grassy ridge walking; navigation is hard in fog."),
    # ── Bucegi (extra) ────────────────────────────────────────────────────
    dict(slug="jepii-mari", name="Jepii Mari – Piatra Arsă", region="Bucegi",
         difficulty=3, duration_minutes=270, distance_m=7000, elevation_gain_m=1250,
         start=(45.4104, 25.5350), summit=(45.4009, 25.4775), summit_elev_m=1950,
         description="Bușteni – Jepii Mari – Cabana Piatra Arsă. Gentler sibling of Jepii Mici; descend by cable car from Babele."),
]

assert len(TRAILS) == 25, f"expected 25 trails, found {len(TRAILS)}"


async def seed_trails(session) -> int:
    """Insert any trails whose slug is missing. Returns number created."""
    existing = set(
        (await session.execute(select(Trail.slug))).scalars().all()
    )
    created = 0
    for t in TRAILS:
        if t["slug"] in existing:
            continue
        start_lat, start_lng = t["start"]
        summit = t["summit"]
        session.add(Trail(
            slug=t["slug"],
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
        ))
        created += 1
    await session.commit()
    return created


def main() -> None:
    async def run() -> None:
        async with AsyncSessionLocal() as session:
            created = await seed_trails(session)
            print(f"Trails seeded: {created} created, {len(TRAILS) - created} already present")

    asyncio.run(run())


if __name__ == "__main__":
    main()
