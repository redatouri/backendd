import os
import re
from pathlib import Path

seed_path = Path(__file__).resolve().parents[1] / "app" / "seed" / "seed_data.py"
prod_dir = Path(__file__).resolve().parents[2] / "frontend" / "public" / "products"

text = seed_path.read_text(encoding="utf-8")
block = text.split("PRODUCTS = [")[1].split("]\n\nasync def upsert")[0]
slugs = re.findall(r'^\s+\("([^"]+)"', block, re.M)
files = os.listdir(prod_dir)
missing = [slug for slug in slugs if not any(name.startswith(f"{slug}-") for name in files)]
print("\n".join(missing))
print(f"COUNT={len(missing)}")
