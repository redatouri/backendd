import asyncio
import shutil
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models import (
    Admin,
    Category,
    CategoryTranslation,
    Product,
    ProductCrossSell,
    ProductImage,
    ProductOffer,
    ProductSpec,
    ProductTranslation,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

CATEGORIES = {
    "cameras": ("Caméras", "كاميرات", "Cameras", ["cameras-mirrorless", "cameras-dslr", "cameras-cinema", "cameras-action", "cameras-webcam-streaming"]),
    "lenses": ("Objectifs", "عدسات", "Lenses", ["lenses-zoom", "lenses-prime", "lenses-cine", "lenses-adapters"]),
    "audio": ("Audio & Micros", "الصوت والميكروفونات", "Audio & Microphones", ["audio-microphones-lavalier", "audio-microphones-shotgun", "audio-wireless", "audio-recorders", "audio-interfaces"]),
    "lighting": ("Éclairage", "الإضاءة", "Lighting", ["lighting-led-panels", "lighting-tubes", "lighting-softboxes", "lighting-stands"]),
    "stabilization": ("Stabilisation", "التثبيت", "Stabilization", ["stabilization-gimbals", "stabilization-tripods", "stabilization-sliders", "stabilization-rigs"]),
    "batteries-power": ("Batteries & Alimentation", "البطاريات والطاقة", "Batteries & Power", ["batteries-camera", "batteries-v-mount", "power-chargers", "power-stations"]),
    "memory-storage": ("Mémoire & Stockage", "الذاكرة والتخزين", "Memory & Storage", ["memory-sd-cf", "memory-ssd", "memory-readers"]),
    "monitors": ("Moniteurs", "شاشات المراقبة", "Monitors", ["monitors-on-camera", "monitors-production", "monitors-recording"]),
    "bags-cases": ("Sacs & Protection", "الحقائب والحماية", "Bags & Cases", ["bags-backpacks", "bags-hard-cases", "bags-slings"]),
    "accessories": ("Accessoires", "ملحقات", "Accessories", ["accessories-filters", "accessories-matte-box", "accessories-follow-focus", "accessories-cables", "accessories-remote"]),
    "studio-packs": ("Packs Studio", "باقات الاستوديو", "Studio Packs", ["studio-packs-photo", "studio-packs-video", "studio-packs-podcast", "studio-packs-streaming"]),
    "action-drones": ("Action & Drones", "أكشن وطائرات", "Action & Drones", ["action-cameras", "drones-consumer", "drones-accessories"]),
}

SUBCATEGORY_FR = {
    "cameras-mirrorless": "Hybrides", "cameras-dslr": "Reflex", "cameras-cinema": "Cinéma", "cameras-action": "Action & Compactes", "cameras-webcam-streaming": "Webcam & Streaming",
    "lenses-zoom": "Zoom", "lenses-prime": "Fixes (Prime)", "lenses-cine": "Cinéma", "lenses-adapters": "Bagues & Adaptateurs",
    "audio-microphones-lavalier": "Micros cravate", "audio-microphones-shotgun": "Micros canon", "audio-wireless": "Sans fil", "audio-recorders": "Enregistreurs", "audio-interfaces": "Interfaces audio",
    "lighting-led-panels": "Panneaux LED", "lighting-tubes": "Tubes & RGB", "lighting-softboxes": "Softbox & Modificateurs", "lighting-stands": "Pieds & Bras",
    "stabilization-gimbals": "Gimbals", "stabilization-tripods": "Trépieds", "stabilization-sliders": "Sliders & Rails", "stabilization-rigs": "Cages & Rigs",
    "batteries-camera": "Batteries caméra", "batteries-v-mount": "V-Mount & Gold Mount", "power-chargers": "Chargeurs", "power-stations": "Stations d'alimentation",
    "memory-sd-cf": "Cartes SD & CF", "memory-ssd": "SSD externe", "memory-readers": "Lecteurs de cartes",
    "monitors-on-camera": "Moniteurs embarqués", "monitors-production": "Moniteurs de production", "monitors-recording": "Enregistreurs moniteur",
    "bags-backpacks": "Sacs à dos", "bags-hard-cases": "Valises rigides", "bags-slings": "Sacs bandoulière",
    "accessories-filters": "Filtres ND & CPL", "accessories-matte-box": "Matte box", "accessories-follow-focus": "Follow focus", "accessories-cables": "Câbles & Convertisseurs", "accessories-remote": "Télécommandes",
    "studio-packs-photo": "Packs Photo", "studio-packs-video": "Packs Vidéo", "studio-packs-podcast": "Packs Podcast", "studio-packs-streaming": "Packs Streaming",
    "action-cameras": "Caméras action", "drones-consumer": "Drones", "drones-accessories": "Accessoires drones",
}

DEFAULT_PRODUCT_SPECS = [("Garantie", "Garantie constructeur")]

PRODUCT_SPECS: dict[str, list[tuple[str, str]]] = {
    "dji-rs4-mini": [
        ("Type de stabilisateur", "Pliable"),
        ("Charge maximale", "2 kg"),
        ("Poids", "890 g (hors trépied)"),
        ("Dimensions", "25,6 x 25,6 x 38,1 cm"),
        ("Autonomie", "Jusqu'à 13 heures"),
        ("Temps de recharge", "1h50 (rapide)"),
        ("Alimentation", "Batterie non amovible"),
        ("Connectique", "2 ports USB-C"),
        ("Communication", "Bluetooth"),
        ("Compatibilité caméras", "Hybrides, smartphone (support requis)"),
        ("Écran intégré", "1,4 pouces"),
        ("Origine", "Fabriqué hors Europe"),
    ],
    "dji-osmo-nano-128gb": [
        ("Capteur", "1/1.3″ CMOS haute performance"),
        ("Résolution vidéo max.", "4K (3840 x 2160) jusqu'à 60 fps"),
        ("Plage dynamique", "13,5 stops"),
        ("Stockage intégré", "128 Go"),
        ("Modes d'enregistrement", "Normal, Pré-enregistrement, Boucle, Auto, Nod/Pat"),
        ("Stabilisation", "EIS : RockSteady / HorizonBalancing / Off"),
        ("Ouverture", "f/2.8 (ultra grand-angle 143°)"),
        ("Profil couleur", "D-Log M, 10-bit"),
        ("Écran Vision Dock", "OLED tactile 1,96″"),
        ("Connectivité", "Wi-Fi, USB 3.1, microSD (export)"),
        ("Autonomie", "Jusqu'à 200 min (dock), 90 min (caméra seule)"),
        ("Charge rapide", "80 % en 20 minutes"),
        ("Étanchéité", "Caméra : 10 m / Dock : IPX4"),
        ("Audio", "2 micros stéréo intégrés, compatible DJI OsmoAudio"),
        ("Poids", "Caméra : 35 g / Dock : 82 g"),
        ("App compatible", "DJI Mimo (Android / iOS)"),
        ("Accessoires inclus", "Lanière magnétique, clip casquette, support ventouse, étui de protection"),
    ],
    "dji-osmo-pocket-3-creator-combo": [
        (
            "Stabilité et Performance Vidéo",
            "Tout d'abord, le DJI Osmo Pocket 3 est équipé d'une stabilisation à 3 axes qui assure des vidéos fluides et sans secousses, même en mouvement. Avec une résolution vidéo 4K à 60 images par seconde, il garantit des images d'une clarté et d'une fluidité impressionnantes. Par conséquent, vos vidéos auront un rendu professionnel, que vous soyez en déplacement ou en action.",
        ),
        (
            "Écran Tactile Intuitif",
            "De plus, ce modèle dispose d'un écran tactile intégré qui facilite la navigation et les réglages. Grâce à cet écran, vous pouvez prévisualiser vos prises de vue, ajuster les paramètres et consulter vos vidéos rapidement et facilement. L'interface utilisateur intuitive améliore l'expérience globale et permet une utilisation simplifiée.",
        ),
        (
            "Accessoires Inclus pour Plus de Flexibilité",
            "Le Creator Combo comprend plusieurs accessoires qui augmentent la flexibilité et les possibilités de création. Parmi ces accessoires, on trouve un trépied, un micro externe, et un contrôle à distance. Ces outils vous permettent de réaliser des prises de vue variées et de capturer un son de qualité supérieure, tout en ayant une grande liberté de mouvement.",
        ),
    ],
}

PRODUCT_DESCRIPTIONS: dict[str, str] = {
    "dji-osmo-pocket-3-creator-combo": (
        "Stabilisation 3 axes, vidéo 4K60 et écran tactile rotatif. "
        "Le Creator Combo inclut trépied, micro externe et accessoires pour un tournage flexible."
    ),
}

REMOVED_PRODUCT_SLUGS = ("dji-mic-2", "dji-rs-4-pro")

PRODUCTS = [
    ("sony-a7iv", "cameras-mirrorless", "Sony A7 IV", "Capturez en 4K 60fps sans compromis", [("Body seul", "SONY-A7IV-BODY", 24999, 29999, 3, None), ("Kit Créateur + 64GB", "SONY-A7IV-KIT", 27499, 31999, 5, "best_value")]),
    ("dji-mic-mini-2-combo", "audio-wireless", "Dji mic mini 2 (2tx + 1 rx + charging case)", "Dji mic mini 2 (2tx + 1 rx + charging case)", [("2 TX + 1 RX + Case", "DJI-MIC-MINI2-COMBO", 1400, None, 8, None)]),
    ("rod-videomic-pro-plus", "audio-microphones-shotgun", "Rode VideoMic Pro+", "Le micro canon préféré des vidéastes", [("Standard", "RODE-VM-PRO-PLUS", 2799, None, 6, None)]),
    ("dji-rs4-mini", "stabilization-gimbals", "Dji rs4 mini", "Dji rs4 mini", [("Standard", "DJI-RS4-MINI", 3400, None, 6, None)]),
    ("dji-rs5", "stabilization-gimbals", "Dji rs5", "Dji rs5", [("Standard", "DJI-RS5", 6100, None, 4, None)]),
    ("dji-osmo-mobile-7", "stabilization-gimbals", "Dji osmo mobile 7", "Dji osmo mobile 7", [("Standard", "DJI-OM7", 950, None, 10, None)]),
    ("dji-osmo-mobile-7p", "stabilization-gimbals", "Dji osmo mobile 7p", "Dji osmo mobile 7p", [("Standard", "DJI-OM7P", 1400, None, 8, None)]),
    ("dji-osmo-mobile-8", "stabilization-gimbals", "Dji osmo mobile 8", "Dji osmo mobile 8", [("Standard", "DJI-OM8", 1800, None, 8, None)]),
    ("dji-osmo-pocket-3-standard", "action-cameras", "Dji osmo pocket 3 standard", "Dji osmo pocket 3 standard", [("Standard", "DJI-OP3-STD", 4500, None, 6, None)]),
    ("dji-osmo-pocket-3-creator-combo", "action-cameras", "Dji osmo pocket 3 creator combo", "Dji osmo pocket 3 creator combo", [("Creator Combo", "DJI-OP3-CREATOR", 6200, None, 5, None)]),
    ("dji-osmo-nano-128gb", "action-cameras", "Dji osmo nano 128gb", "Dji osmo nano 128gb", [("128GB", "DJI-OSMO-NANO-128", 4200, None, 6, None)]),
    ("dji-action-6-standard", "action-cameras", "Dji action 6 standard", "Dji action 6 standard", [("Standard", "DJI-ACTION6-STD", 4800, None, 6, None)]),
    ("dji-action-6-adventure-combo", "action-cameras", "Dji osmo action 6 adventure combo", "Dji osmo action 6 adventure combo", [("Adventure Combo", "DJI-ACTION6-ADV", 5900, None, 5, None)]),
    ("aputure-600d-pro", "lighting-led-panels", "Aputure 600d Pro", "Éclairage daylight 600W pour tournage pro", [("Lumière seule", "APUTURE-600D-PRO", 12499, None, 2, None)]),
    ("sandisk-extreme-pro-256", "memory-sd-cf", "SanDisk Extreme PRO 256GB", "V90 — jamais de dropped frames", [("Carte SD", "SANDISK-EP-256", 899, None, 20, None)]),
    ("sony-np-fz100-twin", "batteries-camera", "Sony NP-FZ100 (x2)", "Autonomie double pour longues journées de tournage", [("Pack 2 batteries", "SONY-NPFZ100-TWIN", 649, None, 15, None)]),
    ("smallrig-cage-a7iv", "stabilization-rigs", "SmallRig Cage Sony A7 IV", "Rig complet prêt à tourner", [("Cage Basic", "SMALLRIG-A7IV-BASIC", 899, None, 10, None)]),
    ("pack-podcast-starter", "studio-packs-podcast", "Pack Podcast Starter", "Lancez votre podcast en un clic", [("Micro + Bras + Interface", "PODCAST-STARTER", 2999, 3499, 7, "limited")]),
    ("gopro-hero-13-black", "action-cameras", "GoPro HERO 13 Black", "Action 5.3K — compact et indestructible", [("Body", "GOPRO-H13-BODY", 3799, None, 9, None), ("Adventure Kit", "GOPRO-H13-ADVENTURE", 4299, None, 5, None)]),
]


async def upsert_category(session: AsyncSession, slug: str, names: tuple[str, str, str], parent_id=None, order: int = 0) -> Category:
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        category = Category(slug=slug, parent_id=parent_id, sort_order=order)
        session.add(category)
        await session.flush()
    for locale, name in zip(("fr", "ar", "en"), names, strict=True):
        translation = await session.scalar(select(CategoryTranslation).where(CategoryTranslation.category_id == category.id, CategoryTranslation.locale == locale))
        if translation is None:
            session.add(CategoryTranslation(category_id=category.id, locale=locale, name=name, description=f"{name} pour créateurs au Maroc."))
    return category


def copy_seed_media() -> None:
    source_dir = Path(__file__).resolve().parent / "assets" / "placeholders"
    if not source_dir.is_dir():
        return
    target_dir = Path(settings.media_root) / "placeholders"
    target_dir.mkdir(parents=True, exist_ok=True)
    for asset in source_dir.iterdir():
        if asset.is_file():
            shutil.copy2(asset, target_dir / asset.name)


async def deactivate_removed_products(session: AsyncSession) -> None:
    for slug in REMOVED_PRODUCT_SLUGS:
        product = await session.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            continue
        product.is_active = False
        cross_sells = await session.scalars(
            select(ProductCrossSell).where(
                (ProductCrossSell.product_id == product.id)
                | (ProductCrossSell.cross_sell_product_id == product.id)
            )
        )
        for link in cross_sells:
            await session.delete(link)


async def seed(session: AsyncSession) -> None:
    copy_seed_media()
    await deactivate_removed_products(session)
    admin = await session.scalar(select(Admin).where(Admin.email == settings.admin_email))
    if admin is None:
        session.add(Admin(email=settings.admin_email, password_hash=hash_password(settings.admin_password), full_name="Moviecam Admin"))

    category_ids: dict[str, object] = {}
    for index, (slug, (fr, ar, en, children)) in enumerate(CATEGORIES.items()):
        parent = await upsert_category(session, slug, (fr, ar, en), order=index)
        category_ids[slug] = parent.id
        for child_index, child_slug in enumerate(children):
            child_name = SUBCATEGORY_FR[child_slug]
            child = await upsert_category(session, child_slug, (child_name, child_name, child_name), parent.id, child_index)
            category_ids[child_slug] = child.id
    await session.flush()

    product_ids: dict[str, object] = {}
    for index, (slug, category_slug, name, headline, offers) in enumerate(PRODUCTS):
        product = await session.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            product = Product(category_id=category_ids[category_slug], slug=slug, rating=Decimal("4.8"), review_count=24 + index * 7, is_featured=index < 6, sort_order=index)
            session.add(product)
            await session.flush()
            for locale in ("fr", "ar", "en"):
                description = PRODUCT_DESCRIPTIONS.get(slug, f"{headline}. Pensé pour les créateurs exigeants au Maroc.")
                session.add(ProductTranslation(product_id=product.id, locale=locale, name=name, headline=headline, subheadline="Équipement professionnel, original et garanti.", description=description, short_description=headline, meta_title=name, meta_description=headline))
            image_count = {
                "dji-osmo-nano-128gb": 1,
                "dji-osmo-mobile-7": 5,
                "dji-osmo-mobile-7p": 2,
                "dji-osmo-mobile-8": 3,
                "dji-action-6-standard": 3,
                "dji-action-6-adventure-combo": 3,
                "dji-rs4-mini": 3,
                "dji-rs5": 3,
            }.get(slug, 4)
            for image_index in range(image_count):
                session.add(ProductImage(product_id=product.id, url=f"/media/placeholders/{slug}-{image_index}.webp", alt_text=name, sort_order=image_index, is_lifestyle=image_index == image_count - 1))
            for sort_order, (spec_key, spec_value) in enumerate(PRODUCT_SPECS.get(slug, DEFAULT_PRODUCT_SPECS)):
                session.add(ProductSpec(product_id=product.id, locale="fr", spec_key=spec_key, spec_value=spec_value, sort_order=sort_order))
            for offer_index, (label, sku, price, compare_at, stock, badge) in enumerate(offers):
                session.add(ProductOffer(product_id=product.id, sku=sku, label=label, price=Decimal(str(price)), compare_at_price=Decimal(str(compare_at)) if compare_at else None, stock=stock, is_default=offer_index == 0, badge=badge, sort_order=offer_index))
        product_ids[slug] = product.id
    await session.flush()

    for source, targets in {"sony-a7iv": ["sandisk-extreme-pro-256", "sony-np-fz100-twin", "smallrig-cage-a7iv"], "dji-mic-mini-2-combo": ["sandisk-extreme-pro-256", "rod-videomic-pro-plus"], "pack-podcast-starter": ["dji-mic-mini-2-combo", "rod-videomic-pro-plus"], "dji-rs4-mini": ["sony-np-fz100-twin", "smallrig-cage-a7iv", "dji-mic-mini-2-combo"], "dji-rs5": ["sony-np-fz100-twin", "smallrig-cage-a7iv", "dji-rs4-mini"], "dji-osmo-mobile-7": ["dji-osmo-pocket-3-standard", "dji-mic-mini-2-combo"], "dji-osmo-mobile-7p": ["dji-osmo-mobile-7", "dji-osmo-pocket-3-standard"], "dji-osmo-mobile-8": ["dji-osmo-mobile-7p", "dji-osmo-pocket-3-standard"], "dji-osmo-pocket-3-standard": ["sandisk-extreme-pro-256", "dji-mic-mini-2-combo"], "dji-osmo-pocket-3-creator-combo": ["sandisk-extreme-pro-256", "dji-osmo-pocket-3-standard", "dji-mic-mini-2-combo"], "dji-osmo-nano-128gb": ["sandisk-extreme-pro-256", "dji-osmo-pocket-3-standard"], "dji-action-6-standard": ["sandisk-extreme-pro-256", "dji-osmo-nano-128gb", "dji-mic-mini-2-combo"], "dji-action-6-adventure-combo": ["dji-action-6-standard", "sandisk-extreme-pro-256", "dji-mic-mini-2-combo"]}.items():
        for priority, target in enumerate(targets):
            exists = await session.scalar(select(ProductCrossSell).where(ProductCrossSell.product_id == product_ids[source], ProductCrossSell.cross_sell_product_id == product_ids[target]))
            if exists is None:
                session.add(ProductCrossSell(product_id=product_ids[source], cross_sell_product_id=product_ids[target], priority=priority))


async def main() -> None:
    async with async_session() as session:
        async with session.begin():
            await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
