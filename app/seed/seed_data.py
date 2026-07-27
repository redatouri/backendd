import asyncio
from decimal import Decimal

from passlib.context import CryptContext
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

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

PRODUCTS = [
    ("sony-a7iv", "cameras-mirrorless", "Sony A7 IV", "Capturez en 4K 60fps sans compromis", [("Body seul", "SONY-A7IV-BODY", 24999, 29999, 3, None), ("Kit Créateur + 64GB", "SONY-A7IV-KIT", 27499, 31999, 5, "best_value")]),
    ("dji-mic-2", "audio-wireless", "DJI Mic 2", "Audio pro sans fil en 30 secondes", [("Duo (2 TX + 1 RX)", "DJI-MIC2-DUO", 3499, None, 8, None), ("Solo (1 TX + 1 RX)", "DJI-MIC2-SOLO", 2199, None, 12, None)]),
    ("rod-videomic-pro-plus", "audio-microphones-shotgun", "Rode VideoMic Pro+", "Le micro canon préféré des vidéastes", [("Standard", "RODE-VM-PRO-PLUS", 2799, None, 6, None)]),
    ("dji-rs-4-pro", "stabilization-gimbals", "DJI RS 4 Pro", "Stabilisation cinéma pour charges lourdes", [("Combo", "DJI-RS4-PRO-COMBO", 8999, None, 4, None)]),
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


async def seed(session: AsyncSession) -> None:
    admin = await session.scalar(select(Admin).where(Admin.email == settings.admin_email))
    if admin is None:
        session.add(Admin(email=settings.admin_email, password_hash=password_context.hash(settings.admin_password), full_name="Moviecam Admin"))

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
                session.add(ProductTranslation(product_id=product.id, locale=locale, name=name, headline=headline, subheadline="Équipement professionnel, original et garanti.", description=f"{headline}. Pensé pour les créateurs exigeants au Maroc.", short_description=headline, meta_title=name, meta_description=headline))
            for image_index in range(4):
                session.add(ProductImage(product_id=product.id, url=f"/media/placeholders/{slug}-{image_index}.webp", alt_text=name, sort_order=image_index, is_lifestyle=image_index == 3))
            session.add(ProductSpec(product_id=product.id, locale="fr", spec_key="Garantie", spec_value="Garantie constructeur", sort_order=0))
            for offer_index, (label, sku, price, compare_at, stock, badge) in enumerate(offers):
                session.add(ProductOffer(product_id=product.id, sku=sku, label=label, price=Decimal(str(price)), compare_at_price=Decimal(str(compare_at)) if compare_at else None, stock=stock, is_default=offer_index == 0, badge=badge, sort_order=offer_index))
        product_ids[slug] = product.id
    await session.flush()

    for source, targets in {"sony-a7iv": ["sandisk-extreme-pro-256", "sony-np-fz100-twin", "smallrig-cage-a7iv"], "dji-mic-2": ["sandisk-extreme-pro-256", "rod-videomic-pro-plus"], "pack-podcast-starter": ["dji-mic-2", "rod-videomic-pro-plus"], "dji-rs-4-pro": ["sony-np-fz100-twin", "smallrig-cage-a7iv"]}.items():
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
