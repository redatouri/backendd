import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 10 * 1024 * 1024


def sanitize_slug(slug: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]", "", slug.lower().strip())
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Slug invalide", "code": "INVALID_SLUG"},
        )
    return cleaned


async def save_product_image(file: UploadFile, slug: str, index: int = 0) -> str:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Format non supporté. Utilisez JPG, PNG ou WebP.",
                "code": "INVALID_IMAGE",
            },
        )

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Fichier vide", "code": "EMPTY_FILE"},
        )
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Image trop volumineuse (max 10 Mo)", "code": "FILE_TOO_LARGE"},
        )

    safe_slug = sanitize_slug(slug)
    ext = ALLOWED_CONTENT_TYPES[content_type]
    uploads_dir = Path(settings.media_root) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_slug}-{index}{ext}"
    (uploads_dir / filename).write_bytes(data)

    return f"{settings.media_url_prefix}/uploads/{filename}"
