from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Category,
    CategoryTranslation,
    Product,
    ProductCrossSell,
    ProductImage,
    ProductOffer,
    ProductSpec,
    ProductTranslation,
)
from app.schemas.category import CategoryChildOut, CategoryOut
from app.schemas.product import (
    CategoryRefOut,
    OfferOut,
    ProductDetailOut,
    ProductImageOut,
    ProductListItemOut,
    ProductSpecOut,
)

LOCALES = ("fr", "ar", "en")


def pick_translation(translations: list, locale: str):
    by_locale = {t.locale: t for t in translations}
    for loc in (locale, "fr", "en", "ar"):
        if loc in by_locale:
            return by_locale[loc]
    return translations[0] if translations else None


def media_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http"):
        return url
    if url.startswith("/media/placeholders/"):
        return "/products/" + url.removeprefix("/media/placeholders/")
    return url


def image_belongs_to_product(url: str, slug: str) -> bool:
    filename = url.rsplit("/", 1)[-1]
    return filename.startswith(f"{slug}-") or filename.startswith(f"{slug}.")


def sanitize_product_images(images: list, slug: str) -> list:
    seen: set[str] = set()
    cleaned: list = []
    for img in sorted(images, key=lambda i: i.sort_order):
        if getattr(img, "is_lifestyle", False):
            continue
        url = media_url(img.url)
        if not url or url in seen or not image_belongs_to_product(url, slug):
            continue
        seen.add(url)
        cleaned.append(img)
    # Product gallery: primary shot only (no lifestyle/scene thumbnails).
    return cleaned[:1]


def offer_out(offer: ProductOffer) -> OfferOut:
    return OfferOut(
        id=offer.id,
        sku=offer.sku,
        label=offer.label,
        price=offer.price,
        compare_at_price=offer.compare_at_price,
        stock=offer.stock,
        is_default=offer.is_default,
        badge=offer.badge,
    )


def default_offer(offers: list[ProductOffer]) -> ProductOffer | None:
    if not offers:
        return None
    for offer in offers:
        if offer.is_default:
            return offer
    return sorted(offers, key=lambda o: o.sort_order)[0]


async def product_count_for_category(db: AsyncSession, category_id: UUID) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.category_id == category_id, Product.is_active.is_(True))
    )
    return int(result or 0)


async def list_categories(db: AsyncSession, locale: str, top: bool = False) -> list[CategoryOut]:
    query = (
        select(Category)
        .where(Category.is_active.is_(True))
        .options(selectinload(Category.translations))
        .order_by(Category.sort_order)
    )
    if top:
        query = query.where(Category.parent_id.is_(None))
    categories = (await db.scalars(query)).all()
    children_map: dict[UUID, list[Category]] = {}
    if top:
        child_rows = (
            await db.scalars(
                select(Category)
                .where(Category.parent_id.is_not(None), Category.is_active.is_(True))
                .options(selectinload(Category.translations))
                .order_by(Category.sort_order)
            )
        ).all()
        for child in child_rows:
            if child.parent_id:
                children_map.setdefault(child.parent_id, []).append(child)

    items: list[CategoryOut] = []
    for cat in categories:
        tr = pick_translation(cat.translations, locale)
        if tr is None:
            continue
        children_out: list[CategoryChildOut] = []
        for child in children_map.get(cat.id, []):
            ctr = pick_translation(child.translations, locale)
            if ctr:
                count = await product_count_for_category(db, child.id)
                children_out.append(CategoryChildOut(slug=child.slug, name=ctr.name, product_count=count))
        count = await product_count_for_category(db, cat.id)
        items.append(
            CategoryOut(
                id=cat.id,
                slug=cat.slug,
                name=tr.name,
                description=tr.description,
                image_url=f"/media/placeholders/collection-{cat.slug}.webp",
                product_count=count,
                children=children_out,
            )
        )
    return items


async def get_category(db: AsyncSession, slug: str, locale: str) -> CategoryOut | None:
    cat = await db.scalar(
        select(Category)
        .where(Category.slug == slug, Category.is_active.is_(True))
        .options(selectinload(Category.translations))
    )
    if cat is None:
        return None
    tr = pick_translation(cat.translations, locale)
    if tr is None:
        return None
    children = (
        await db.scalars(
            select(Category)
            .where(Category.parent_id == cat.id, Category.is_active.is_(True))
            .options(selectinload(Category.translations))
            .order_by(Category.sort_order)
        )
    ).all()
    children_out = []
    for child in children:
        ctr = pick_translation(child.translations, locale)
        if ctr:
            count = await product_count_for_category(db, child.id)
            children_out.append(CategoryChildOut(slug=child.slug, name=ctr.name, product_count=count))
    count = await product_count_for_category(db, cat.id)
    return CategoryOut(
        id=cat.id,
        slug=cat.slug,
        name=tr.name,
        description=tr.description,
        image_url=f"/media/placeholders/collection-{cat.slug}.webp",
        product_count=count,
        children=children_out,
    )


async def serialize_product_list_item(
    db: AsyncSession, product: Product, locale: str
) -> ProductListItemOut | None:
    tr = pick_translation(product.translations, locale)
    if tr is None:
        return None
    offers = sorted(product.offers, key=lambda o: o.sort_order)
    d_offer = default_offer(offers)
    images = sanitize_product_images(product.images, product.slug)
    primary = media_url(images[0].url) if images else None
    cat_ref = None
    if product.category:
        ctr = pick_translation(product.category.translations, locale)
        if ctr:
            cat_ref = CategoryRefOut(slug=product.category.slug, name=ctr.name)
    return ProductListItemOut(
        id=product.id,
        slug=product.slug,
        name=tr.name,
        headline=tr.headline,
        subheadline=tr.subheadline,
        rating=product.rating,
        review_count=product.review_count,
        primary_image=primary,
        default_offer=offer_out(d_offer) if d_offer else None,
        category=cat_ref,
    )


async def list_products(
    db: AsyncSession,
    locale: str,
    *,
    category: str | None = None,
    featured: bool | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "popular",
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
) -> tuple[list[ProductListItemOut], int]:
    query = (
        select(Product)
        .where(Product.is_active.is_(True))
        .options(
            selectinload(Product.translations),
            selectinload(Product.offers),
            selectinload(Product.images),
            selectinload(Product.category).selectinload(Category.translations),
        )
    )
    if category:
        cat = await db.scalar(select(Category).where(Category.slug == category))
        if cat:
            child_ids = (
                await db.scalars(select(Category.id).where(Category.parent_id == cat.id))
            ).all()
            ids = [cat.id, *child_ids]
            query = query.where(Product.category_id.in_(ids))
    if featured is True:
        query = query.where(Product.is_featured.is_(True))
    if sort == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort == "price_asc":
        query = query.order_by(Product.sort_order)
    elif sort == "price_desc":
        query = query.order_by(Product.sort_order.desc())
    else:
        query = query.order_by(Product.is_featured.desc(), Product.sort_order)

    products = (await db.scalars(query)).all()
    items: list[ProductListItemOut] = []
    for product in products:
        serialized = await serialize_product_list_item(db, product, locale)
        if serialized is None:
            continue
        if in_stock and (serialized.default_offer is None or serialized.default_offer.stock <= 0):
            continue
        if min_price is not None and (
            serialized.default_offer is None or serialized.default_offer.price < min_price
        ):
            continue
        if max_price is not None and (
            serialized.default_offer is None or serialized.default_offer.price > max_price
        ):
            continue
        items.append(serialized)

    total = len(items)
    start = (page - 1) * limit
    return items[start : start + limit], total


async def get_product(db: AsyncSession, slug: str, locale: str) -> ProductDetailOut | None:
    product = await db.scalar(
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(
            selectinload(Product.translations),
            selectinload(Product.offers),
            selectinload(Product.images),
            selectinload(Product.specs),
            selectinload(Product.category).selectinload(Category.translations),
        )
    )
    if product is None:
        return None
    tr = pick_translation(product.translations, locale)
    if tr is None:
        return None
    cross_rows = (
        await db.scalars(
            select(ProductCrossSell)
            .where(ProductCrossSell.product_id == product.id)
            .order_by(ProductCrossSell.priority)
        )
    ).all()
    cross_ids = [row.cross_sell_product_id for row in cross_rows]
    cross_sells: list[ProductListItemOut] = []
    if cross_ids:
        cross_products = (
            await db.scalars(
                select(Product)
                .where(Product.id.in_(cross_ids), Product.is_active.is_(True))
                .options(
                    selectinload(Product.translations),
                    selectinload(Product.offers),
                    selectinload(Product.images),
                    selectinload(Product.category).selectinload(Category.translations),
                )
            )
        ).all()
        by_id = {p.id: p for p in cross_products}
        for cid in cross_ids:
            cp = by_id.get(cid)
            if cp:
                item = await serialize_product_list_item(db, cp, locale)
                if item:
                    cross_sells.append(item)
    cat_ref = None
    if product.category:
        ctr = pick_translation(product.category.translations, locale)
        if ctr:
            cat_ref = CategoryRefOut(slug=product.category.slug, name=ctr.name)
    specs = [
        ProductSpecOut(key=s.spec_key, value=s.spec_value)
        for s in sorted(product.specs, key=lambda x: x.sort_order)
        if s.locale == locale or s.locale == "fr"
    ]
    return ProductDetailOut(
        id=product.id,
        slug=product.slug,
        name=tr.name,
        headline=tr.headline,
        subheadline=tr.subheadline,
        description=tr.description,
        short_description=tr.short_description,
        rating=product.rating,
        review_count=product.review_count,
        images=[
            ProductImageOut(
                url=media_url(img.url) or "",
                alt_text=img.alt_text,
                is_lifestyle=img.is_lifestyle,
                sort_order=img.sort_order,
            )
            for img in sanitize_product_images(product.images, product.slug)
        ],
        offers=[offer_out(o) for o in sorted(product.offers, key=lambda o: o.sort_order)],
        specs=specs,
        cross_sells=cross_sells[:6],
        category=cat_ref,
    )


async def get_cross_sells(
    db: AsyncSession, product_ids: list[UUID], locale: str, limit: int = 4
) -> list[ProductListItemOut]:
    if not product_ids:
        return []
    manual = (
        await db.scalars(
            select(ProductCrossSell)
            .where(ProductCrossSell.product_id.in_(product_ids))
            .order_by(ProductCrossSell.priority)
        )
    ).all()
    seen: set[UUID] = set(product_ids)
    ordered_ids: list[UUID] = []
    for row in manual:
        if row.cross_sell_product_id not in seen:
            seen.add(row.cross_sell_product_id)
            ordered_ids.append(row.cross_sell_product_id)
    if len(ordered_ids) < limit:
        fallback = (
            await db.scalars(
                select(Product)
                .where(Product.is_active.is_(True), Product.id.not_in(list(seen)))
                .options(
                    selectinload(Product.translations),
                    selectinload(Product.offers),
                    selectinload(Product.images),
                    selectinload(Product.category).selectinload(Category.translations),
                )
                .limit(limit)
            )
        ).all()
        for p in fallback:
            if p.id not in seen:
                ordered_ids.append(p.id)
                seen.add(p.id)
    items: list[ProductListItemOut] = []
    if not ordered_ids:
        return items
    products = (
        await db.scalars(
            select(Product)
            .where(Product.id.in_(ordered_ids[:limit]))
            .options(
                selectinload(Product.translations),
                selectinload(Product.offers),
                selectinload(Product.images),
                selectinload(Product.category).selectinload(Category.translations),
            )
        )
    ).all()
    by_id = {p.id: p for p in products}
    for pid in ordered_ids[:limit]:
        p = by_id.get(pid)
        if p:
            item = await serialize_product_list_item(db, p, locale)
            if item:
                items.append(item)
    return items
