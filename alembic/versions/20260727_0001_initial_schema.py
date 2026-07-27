"""create Moviecam initial schema

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260727_0001"
down_revision = None
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=True)
timestamp = sa.DateTime(timezone=True)


def id_column() -> sa.Column:
    return sa.Column("id", uuid, primary_key=True, nullable=False)


def timestamps() -> list[sa.Column]:
    return [sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False)]


def upgrade() -> None:
    op.create_table(
        "admins",
        id_column(),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "categories",
        id_column(),
        sa.Column("parent_id", uuid, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "category_translations",
        id_column(),
        sa.Column("category_id", uuid, sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("meta_title", sa.String(255), server_default="", nullable=False),
        sa.Column("meta_description", sa.Text(), server_default="", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("category_id", "locale"),
    )
    op.create_table(
        "products",
        id_column(),
        sa.Column("category_id", uuid, sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False, unique=True),
        sa.Column("rating", sa.Numeric(2, 1), server_default="4.5", nullable=False),
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "product_translations",
        id_column(),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("headline", sa.String(255), server_default="", nullable=False),
        sa.Column("subheadline", sa.String(500), server_default="", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("short_description", sa.String(500), server_default="", nullable=False),
        sa.Column("meta_title", sa.String(255), server_default="", nullable=False),
        sa.Column("meta_description", sa.Text(), server_default="", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("product_id", "locale"),
    )
    op.create_table(
        "product_images",
        id_column(),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(255), server_default="", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_lifestyle", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "product_offers",
        id_column(),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("compare_at_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("badge", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "product_specs",
        id_column(),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("spec_key", sa.String(100), nullable=False),
        sa.Column("spec_value", sa.String(500), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *timestamps(),
    )
    op.create_table(
        "product_cross_sells",
        id_column(),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cross_sell_product_id", uuid, sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("product_id", "cross_sell_product_id"),
    )
    op.create_table(
        "orders",
        id_column(),
        sa.Column("order_number", sa.String(20), nullable=False, unique=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("payment_method", sa.String(20), server_default="cod", nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("customer", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "order_items",
        id_column(),
        sa.Column("order_id", uuid, sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("offer_id", uuid, sa.ForeignKey("product_offers.id"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("offer_label", sa.String(255), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        *timestamps(),
    )
    op.create_table("order_sequences", sa.Column("year", sa.Integer(), primary_key=True), sa.Column("last_number", sa.Integer(), server_default="0", nullable=False))
    op.create_index("idx_products_category", "products", ["category_id"])
    op.create_index("idx_products_featured", "products", ["is_featured"], postgresql_where=sa.text("is_active = true"))
    op.create_index("idx_orders_status", "orders", ["status"])
    op.create_index("idx_orders_created", "orders", ["created_at"], postgresql_ops={"created_at": "DESC"})
    op.create_index("idx_product_translations_locale", "product_translations", ["locale"])
    op.create_index("idx_category_translations_locale", "category_translations", ["locale"])


def downgrade() -> None:
    for table in ("order_sequences", "order_items", "orders", "product_cross_sells", "product_specs", "product_offers", "product_images", "product_translations", "products", "category_translations", "categories", "admins"):
        op.drop_table(table)
