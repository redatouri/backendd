import re
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
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
from app.schemas.admin_product import (
    AdminCategoryOptionOut,
    AdminImageIn,
    AdminOfferIn,
    AdminProductCreateIn,
    AdminProductDetailOut,
    AdminProductListItemOut,
    AdminProductUpdateIn,
    AdminSpecIn,
    AdminTranslationIn,
)
from app.services.product_service import LOCALES, default_offer, pick_translation

DEFAULT_SUBHEADLINE = "Équipement professionnel, original et garanti."


def slugify(value: str) -> str:
    slug = value.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:150]


def sku_from_slug(slug: str) -> str:
    return slug.upper().replace("-", "_")[:50]


def fill_translations(translations: list[AdminTranslationIn]) -> list[AdminTranslationIn]:
    if translations:
        return translations
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"message": "At least one translation is required", "code": "VALIDATION_ERROR"},
    )


def ensure_all_locales(base: AdminTranslationIn) -> list[AdminTranslationIn]:
    by_locale = {item.locale: item for item in fill_translations([base])}
    results: list[AdminTranslationIn] = []
    for locale in LOCALES:
        if locale in by_locale:
            results.append(by_locale[locale])
        else:
            results.append(
                AdminTranslationIn(
                    locale=locale,
                    name=base.name,
                    headline=base.headline or base.name,
                    subheadline=base.subheadline or DEFAULT_SUBHEADLINE,
                    description=base.description or f"{base.headline or base.name}. Pensé pour les créateurs exigeants au Maroc.",
                    short_description=base.short_description or base.headline or base.name,
                    meta_title=base.meta_title or base.name,
                    meta_description=base.meta_description or base.headline or base.name,
                )
            )
    return results


def product_to_admin_list_item(product: Product) -> AdminProductListItemOut:
    translation = pick_translation(product.translations, "fr")
    offer = default_offer(product.offers)
    primary_image = None
    if product.images:
        primary_image = sorted(product.images, key=lambda image: image.sort_order)[0].url
    category_translation = (
        pick_translation(product.category.translations, "fr") if product.category else None
    )
    return AdminProductListItemOut(
        id=product.id,
        slug=product.slug,
        name=translation.name if translation else product.slug,
        category_id=product.category_id,
        category_slug=product.category.slug if product.category else None,
        category_name=category_translation.name if category_translation else None,
        price=offer.price if offer else None,
        stock=offer.stock if offer else None,
        offer_id=offer.id if offer else None,
        is_active=product.is_active,
        is_featured=product.is_featured,
        primary_image=primary_image,
    )


def product_to_admin_detail(product: Product) -> AdminProductDetailOut:
    category_translation = (
        pick_translation(product.category.translations, "fr") if product.category else None
    )
    cross_sells = getattr(product, "cross_sells_out", [])
    return AdminProductDetailOut(
        id=product.id,
        slug=product.slug,
        category_id=product.category_id,
        category_slug=product.category.slug if product.category else None,
        is_active=product.is_active,
        is_featured=product.is_featured,
        sort_order=product.sort_order,
        translations=[
            AdminTranslationIn(
                locale=t.locale,
                name=t.name,
                headline=t.headline,
                subheadline=t.subheadline,
                description=t.description,
                short_description=t.short_description,
                meta_title=t.meta_title,
                meta_description=t.meta_description,
            )
            for t in product.translations
        ],
        offers=[
            AdminOfferIn(
                id=o.id,
                sku=o.sku,
                label=o.label,
                price=o.price,
                compare_at_price=o.compare_at_price,
                stock=o.stock,
                is_default=o.is_default,
                badge=o.badge,
                sort_order=o.sort_order,
            )
            for o in sorted(product.offers, key=lambda offer: offer.sort_order)
        ],
        images=[
            AdminImageIn(
                url=i.url,
                alt_text=i.alt_text,
                sort_order=i.sort_order,
                is_lifestyle=i.is_lifestyle,
            )
            for i in sorted(product.images, key=lambda image: image.sort_order)
        ],
        specs=[
            AdminSpecIn(
                locale=s.locale,
                spec_key=s.spec_key,
                spec_value=s.spec_value,
                sort_order=s.sort_order,
            )
            for s in sorted(product.specs, key=lambda spec: spec.sort_order)
        ],
        cross_sell_ids=cross_sells,
    )


async def load_product(db: AsyncSession, product_id: UUID) -> Product | None:
    product = await db.scalar(
        select(Product)
        .where(Product.id == product_id)
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
    cross_sells = (
        await db.scalars(
            select(ProductCrossSell.cross_sell_product_id).where(
                ProductCrossSell.product_id == product.id
            )
        )
    ).all()
    product.cross_sells_out = list(cross_sells)
    return product


async def list_admin_categories(db: AsyncSession) -> list[AdminCategoryOptionOut]:
    categories = (
        await db.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .options(selectinload(Category.translations))
            .order_by(Category.sort_order, Category.slug)
        )
    ).all()
    items: list[AdminCategoryOptionOut] = []
    for category in categories:
        translation = pick_translation(category.translations, "fr")
        if translation is None:
            continue
        items.append(
            AdminCategoryOptionOut(
                id=category.id,
                slug=category.slug,
                name=translation.name,
            )
        )
    return items


async def list_admin_products(
    db: AsyncSession,
    *,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
) -> tuple[list[AdminProductListItemOut], int]:
    query = (
        select(Product)
        .options(
            selectinload(Product.translations),
            selectinload(Product.offers),
            selectinload(Product.images),
            selectinload(Product.category).selectinload(Category.translations),
        )
        .order_by(Product.sort_order, Product.slug)
    )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Product.slug.ilike(pattern),
                Product.translations.any(ProductTranslation.name.ilike(pattern)),
                Product.offers.any(ProductOffer.sku.ilike(pattern)),
            )
        )
    products = (await db.scalars(query)).all()
    total = len(products)
    start = (page - 1) * limit
    page_items = products[start : start + limit]
    return [product_to_admin_list_item(product) for product in page_items], total


async def create_admin_product(db: AsyncSession, payload: AdminProductCreateIn) -> AdminProductDetailOut:
    existing = await db.scalar(select(Product).where(Product.slug == payload.slug))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Slug already exists", "code": "SLUG_EXISTS"},
        )

    category = await db.get(Category, payload.category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Category not found", "code": "NOT_FOUND"},
        )

    product = Product(
        category_id=payload.category_id,
        slug=payload.slug,
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        sort_order=payload.sort_order,
    )
    db.add(product)
    await db.flush()

    translations = payload.translations
    if len(translations) == 1:
        translations = ensure_all_locales(translations[0])

    for translation in translations:
        db.add(
            ProductTranslation(
                product_id=product.id,
                locale=translation.locale,
                name=translation.name,
                headline=translation.headline or translation.name,
                subheadline=translation.subheadline or DEFAULT_SUBHEADLINE,
                description=translation.description
                or f"{translation.headline or translation.name}. Pensé pour les créateurs exigeants au Maroc.",
                short_description=translation.short_description or translation.headline or translation.name,
                meta_title=translation.meta_title or translation.name,
                meta_description=translation.meta_description or translation.headline or translation.name,
            )
        )

    offers = payload.offers
    if not offers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "At least one offer is required", "code": "VALIDATION_ERROR"},
        )
    for index, offer in enumerate(offers):
        db.add(
            ProductOffer(
                product_id=product.id,
                sku=offer.sku,
                label=offer.label,
                price=offer.price,
                compare_at_price=offer.compare_at_price,
                stock=offer.stock,
                is_default=offer.is_default if index == 0 else False,
                badge=offer.badge,
                sort_order=offer.sort_order or index,
            )
        )

    for index, image in enumerate(payload.images):
        db.add(
            ProductImage(
                product_id=product.id,
                url=image.url,
                alt_text=image.alt_text or translations[0].name,
                sort_order=image.sort_order or index,
                is_lifestyle=image.is_lifestyle,
            )
        )

    for index, spec in enumerate(payload.specs or []):
        db.add(
            ProductSpec(
                product_id=product.id,
                locale=spec.locale,
                spec_key=spec.spec_key,
                spec_value=spec.spec_value,
                sort_order=spec.sort_order or index,
            )
        )

    for priority, cross_sell_id in enumerate(payload.cross_sell_ids):
        db.add(
            ProductCrossSell(
                product_id=product.id,
                cross_sell_product_id=cross_sell_id,
                priority=priority,
            )
        )

    await db.commit()
    loaded = await load_product(db, product.id)
    assert loaded is not None
    return product_to_admin_detail(loaded)


async def update_admin_product(
    db: AsyncSession,
    product_id: UUID,
    payload: AdminProductUpdateIn,
) -> AdminProductDetailOut:
    product = await load_product(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Product not found", "code": "NOT_FOUND"},
        )

    if payload.slug and payload.slug != product.slug:
        existing = await db.scalar(
            select(Product).where(Product.slug == payload.slug, Product.id != product.id)
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Slug already exists", "code": "SLUG_EXISTS"},
            )
        product.slug = payload.slug

    if payload.category_id is not None:
        category = await db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Category not found", "code": "NOT_FOUND"},
            )
        product.category_id = payload.category_id

    if payload.is_active is not None:
        product.is_active = payload.is_active
    if payload.is_featured is not None:
        product.is_featured = payload.is_featured
    if payload.sort_order is not None:
        product.sort_order = payload.sort_order

    if payload.translations is not None:
        for translation in product.translations:
            await db.delete(translation)
        await db.flush()
        translations = payload.translations
        if len(translations) == 1:
            translations = ensure_all_locales(translations[0])
        for translation in translations:
            db.add(
                ProductTranslation(
                    product_id=product.id,
                    locale=translation.locale,
                    name=translation.name,
                    headline=translation.headline or translation.name,
                    subheadline=translation.subheadline or DEFAULT_SUBHEADLINE,
                    description=translation.description
                    or f"{translation.headline or translation.name}. Pensé pour les créateurs exigeants au Maroc.",
                    short_description=translation.short_description or translation.headline or translation.name,
                    meta_title=translation.meta_title or translation.name,
                    meta_description=translation.meta_description or translation.headline or translation.name,
                )
            )

    if payload.offers is not None:
        for offer in product.offers:
            await db.delete(offer)
        await db.flush()
        for index, offer in enumerate(payload.offers):
            db.add(
                ProductOffer(
                    product_id=product.id,
                    sku=offer.sku,
                    label=offer.label,
                    price=offer.price,
                    compare_at_price=offer.compare_at_price,
                    stock=offer.stock,
                    is_default=offer.is_default,
                    badge=offer.badge,
                    sort_order=offer.sort_order or index,
                )
            )

    if payload.images is not None:
        for image in product.images:
            await db.delete(image)
        await db.flush()
        name = product.translations[0].name if product.translations else product.slug
        for index, image in enumerate(payload.images):
            db.add(
                ProductImage(
                    product_id=product.id,
                    url=image.url,
                    alt_text=image.alt_text or name,
                    sort_order=image.sort_order or index,
                    is_lifestyle=image.is_lifestyle,
                )
            )

    if payload.specs is not None:
        for spec in product.specs:
            await db.delete(spec)
        await db.flush()
        for index, spec in enumerate(payload.specs):
            db.add(
                ProductSpec(
                    product_id=product.id,
                    locale=spec.locale,
                    spec_key=spec.spec_key,
                    spec_value=spec.spec_value,
                    sort_order=spec.sort_order or index,
                )
            )

    if payload.cross_sell_ids is not None:
        existing_links = (
            await db.scalars(select(ProductCrossSell).where(ProductCrossSell.product_id == product.id))
        ).all()
        for link in existing_links:
            await db.delete(link)
        await db.flush()
        for priority, cross_sell_id in enumerate(payload.cross_sell_ids):
            db.add(
                ProductCrossSell(
                    product_id=product.id,
                    cross_sell_product_id=cross_sell_id,
                    priority=priority,
                )
            )

    await db.commit()
    loaded = await load_product(db, product.id)
    assert loaded is not None
    return product_to_admin_detail(loaded)


async def delete_admin_product(db: AsyncSession, product_id: UUID) -> None:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Product not found", "code": "NOT_FOUND"},
        )
    product.is_active = False
    await db.commit()
