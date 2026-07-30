import asyncio
import os
import shutil
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy import func, select
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

REMOVED_PRODUCT_SLUGS = (
    "dji-mic-2",
    "smallrig-cage-a7iv",
    "gopro-hero-13-black",
    "pack-gopro",
    "rod-videomic-pro-plus",
    "aputure-600d-pro",
    "sandisk-extreme-pro-256",
    "sony-np-fz100-twin",
    "pack-podcast-starter",
)

PRODUCT_IMAGES = {
    "sony-a7iv": "/media/placeholders/sony-a7iv-0.png",
    "sony-fx3": "/media/placeholders/sony-fx3-0.png",
    "sony-a7iii": "/media/placeholders/sony-a7iii-0.png",
    "sony-fe-50mm-f18": "/media/placeholders/sony-fe-50mm-f18-0.png",
    "sony-fe-24-70-f4": "/media/placeholders/sony-fe-24-70-f4-0.png",
    "sony-fe-24-70-f28-gm": "/media/placeholders/sony-fe-24-70-f28-gm-0.png",
    "sony-np-fz100": "/media/placeholders/sony-np-fz100-0.png",
    "sony-fx30": "/media/placeholders/sony-fx30-0.png",
    "dji-osmo-pocket-4-creator-combo": "/media/placeholders/dji-osmo-pocket-4-creator-combo-0.png",
    "dji-osmo-pocket-4-standard": "/media/placeholders/dji-osmo-pocket-4-standard-0.png",
    "godox-v1-sony": "/media/placeholders/godox-v1-sony-0.png",
    "godox-ak-r22": "/media/placeholders/godox-ak-r22-0.png",
    "godox-lc500r-mini": "/media/placeholders/godox-lc500r-mini-0.png",
    "kf-concept-nano-b-nd2-400": "/media/placeholders/kf-concept-nano-b-nd2-400-0.png",
    "hollyland-lark-m2s": "/media/placeholders/hollyland-lark-m2s-0.png",
    "torche-r8-led-rgb": "/media/placeholders/torche-r8-led-rgb-0.png",
    "desview-p5-ii": "/media/placeholders/desview-p5-ii-0.png",
    "feelworld-f5-prox": "/media/placeholders/feelworld-f5-prox-0.png",
    "zoom-h8": "/media/placeholders/zoom-h8-0.png",
    "lexar-multi-card-reader": "/media/placeholders/lexar-multi-card-reader-0.png",
    "c-stand-support": "/media/placeholders/c-stand-support-0.png",
    "stand-inox": "/media/placeholders/stand-inox-0.png",
    "fond-papier-272-11m-bleu": "/media/placeholders/fond-papier-272-11m-bleu-0.png",
    "fond-papier-272-11m-blanc": "/media/placeholders/fond-papier-272-11m-blanc-0.png",
    "fond-papier-272-11m-rouge": "/media/placeholders/fond-papier-272-11m-rouge-0.png",
    "fond-papier-272-11m-jaune": "/media/placeholders/fond-papier-272-11m-jaune-0.png",
    "fond-papier-272-11m-noir": "/media/placeholders/fond-papier-272-11m-noir-0.png",
    "fond-papier-272-11m-vert": "/media/placeholders/fond-papier-272-11m-vert-0.png",
    "derouleur-fond-mural-3-fonds": "/media/placeholders/derouleur-fond-mural-3-fonds-0.png",
    "derouleur-fond-mural-4-fonds": "/media/placeholders/derouleur-fond-mural-4-fonds-0.png",
    "mini-c-stand": "/media/placeholders/mini-c-stand-0.png",
    "lexar-professional-128-v90-uhs2": "/media/placeholders/lexar-professional-128-v90-uhs2-0.png",
    "sandisk-extreme-pro-128-v30": "/media/placeholders/sandisk-extreme-pro-128-v30-0.png",
    "sandisk-extreme-pro-64-v30": "/media/placeholders/sandisk-extreme-pro-64-v30-0.png",
    "sandisk-extreme-pro-sdxc-200-v30": "/media/placeholders/sandisk-extreme-pro-sdxc-200-v30-0.png",
    "boya-by-bm6060": "/media/placeholders/boya-by-bm6060-0.png",
    "godox-iflash-im30": "/media/placeholders/godox-iflash-im30-0.png",
    "dji-rs-4-pro-combo": "/media/placeholders/dji-rs-4-pro-combo-0.png",
    "dji-rs-4-pro": "/media/placeholders/dji-rs-4-pro-0.png",
    "dji-rs-5-combo": "/media/placeholders/dji-rs-5-combo-0.png",
    "dji-rs-4": "/media/placeholders/dji-rs-4-0.png",
    "dji-mic-3-2tx-1rx-case": "/media/placeholders/dji-mic-3-2tx-1rx-case-0.png",
    "dji-mic-3-1tx-1rx": "/media/placeholders/dji-mic-3-1tx-1rx-0.png",
    "sac-lolobo-grand": "/media/placeholders/sac-lolobo-grand-0.png",
    "sac-camera": "/media/placeholders/sac-camera-0.png",
    "tripod-candc-dc-999": "/media/placeholders/tripod-candc-dc-999-0.png",
    "tripod-candc-dc-6917": "/media/placeholders/tripod-candc-dc-6917-0.png",
    "tripod-candc-dc-6918": "/media/placeholders/tripod-candc-dc-6918-0.png",
    "feelworld-tp10": "/media/placeholders/feelworld-tp10-0.png",
    "kodak-gold-200-film-bundle": "/media/placeholders/kodak-gold-200-film-bundle-0.png",
    "deity-v-mic-d3-pro": "/media/placeholders/deity-v-mic-d3-pro-0.png",
    "rode-videomic-go": "/media/placeholders/rode-videomic-go-0.png",
    "rode-wireless-go-ii-dual": "/media/placeholders/rode-wireless-go-ii-dual-0.png",
    "rode-wireless-go-ii-single": "/media/placeholders/rode-wireless-go-ii-single-0.png",
    "tamron-28-75-f28-g2-sony-fe": "/media/placeholders/tamron-28-75-f28-g2-sony-fe-0.png",
    "feelworld-f7-plus": "/media/placeholders/feelworld-f7-plus-0.png",
    "zhiyun-torche-m20": "/media/placeholders/zhiyun-torche-m20-0.png",
    "vrig-fd-140-rgb": "/media/placeholders/vrig-fd-140-rgb-0.png",
    "canon-lc-e6": "/media/placeholders/canon-lc-e6-0.png",
    "canon-lc-e17": "/media/placeholders/canon-lc-e17-0.png",
    "canon-lc-e10": "/media/placeholders/canon-lc-e10-0.png",
    "sony-bc-qz1": "/media/placeholders/sony-bc-qz1-0.png",
    "canon-lc-e8": "/media/placeholders/canon-lc-e8-0.png",
    "pisen-fz100-charging-box": "/media/placeholders/pisen-fz100-charging-box-0.png",
    "sony-np-f970": "/media/placeholders/sony-np-f970-0.png",
}

PRODUCTS = [
    ("sony-a7iv", "cameras-mirrorless", "Sony alpha 7 iv Neuf", "Sony alpha 7 iv Neuf", [("Neuf", "SONY-A7IV-NEUF", 21999, None, 3, None)]),
    ("sony-fx3", "cameras-cinema", "Sony fx3 neuf", "Sony fx3 neuf", [("Neuf", "SONY-FX3-NEUF", 36999, None, 2, None)]),
    ("sony-a7iii", "cameras-mirrorless", "Sony a7 iii neuf", "Sony a7 iii neuf", [("Neuf", "SONY-A7III-NEUF", 13999, None, 4, None)]),
    ("sony-fe-50mm-f18", "lenses-prime", "Sony 50mm f1.8 neuf", "Sony 50mm f1.8 neuf", [("Neuf", "SONY-FE50F18-NEUF", 2499, None, 8, None)]),
    ("sony-fe-24-70-f4", "lenses-zoom", "Sony fe 24-70mm f/4 g oss carl zeiss - neuf", "Sony fe 24-70mm f/4 g oss carl zeiss - neuf", [("Neuf", "SONY-FE2470F4-NEUF", 6399, None, 5, None)]),
    ("sony-fe-24-70-f28-gm", "lenses-zoom", "Sony fe 24-70mm f/2.8 GM - neuf", "Sony fe 24-70mm f/2.8 GM - neuf", [("Neuf", "SONY-FE2470F28GM-NEUF", 15699, None, 3, None)]),
    ("sony-np-fz100", "batteries-camera", "Sony NP-FZ100", "Sony NP-FZ100", [("Neuf", "SONY-NPFZ100", 300, None, 15, None)]),
    ("sony-fx30", "cameras-cinema", "Sony fx30 bon occasion", "Sony fx30 bon occasion", [("Bon occasion", "SONY-FX30-OCC", 15999, None, 1, None)]),
    ("dji-osmo-pocket-4-creator-combo", "action-cameras", "Dji osmo pocket 4 creator combo", "Dji osmo pocket 4 creator combo", [("Creator Combo", "DJI-OP4-CREATOR", 7800, None, 5, None)]),
    ("dji-osmo-pocket-4-standard", "action-cameras", "Dji osmo pocket 4 standard", "Dji osmo pocket 4 standard", [("Standard", "DJI-OP4-STD", 6100, None, 6, None)]),
    ("godox-v1-sony", "lighting-led-panels", "Godox v1 sony", "Godox v1 sony", [("Neuf", "GODOX-V1-SONY", 1999, None, 8, None)]),
    ("godox-ak-r22", "lighting-softboxes", "Godox ak-r22", "Godox ak-r22", [("Neuf", "GODOX-AKR22", 299, None, 12, None)]),
    ("godox-lc500r-mini", "lighting-tubes", "Godox lc500r mini", "Godox lc500r mini", [("Neuf", "GODOX-LC500R-MINI", 1450, None, 6, None)]),
    ("kf-concept-nano-b-nd2-400", "accessories-filters", "K&F Concept Nano-B Filtre ND2-400", "K&F Concept Nano-B Filtre ND2-400", [("Neuf", "KF-NANOB-ND2400", 350, None, 10, None)]),
    ("hollyland-lark-m2s", "audio-wireless", "Hollyland lark m2s", "Hollyland lark m2s", [("Neuf", "HOLLYLAND-LARK-M2S", 1400, None, 8, None)]),
    ("torche-r8-led-rgb", "lighting-led-panels", "Torche R8 LED RGB", "Torche R8 LED RGB", [("Neuf", "TORCHE-R8-RGB", 899, None, 10, None)]),
    ("desview-p5-ii", "monitors-on-camera", "BESTVIEW DESVIEW P5 II 5,5'' Full HD", "BESTVIEW DESVIEW P5 II 5,5'' Full HD", [("Neuf", "DESVIEW-P5-II", 1500, None, 5, None)]),
    ("feelworld-f5-prox", "monitors-on-camera", "FEELWORLD F5 PROX 5.5″ Écran Tactile (4K-HDMI) DSLR Caméra Moniteur de Champ 1600nit", "FEELWORLD F5 PROX 5.5″ Écran Tactile (4K-HDMI) DSLR Caméra Moniteur de Champ 1600nit", [("Neuf", "FEELWORLD-F5-PROX", 1800, None, 4, None)]),
    ("zoom-h8", "audio-recorders", "Zoom h8", "Zoom h8", [("Neuf", "ZOOM-H8", 5800, None, 3, None)]),
    ("lexar-multi-card-reader", "memory-readers", "Lecteur carte Lexar Multi-Card 3in1 USB 3.1", "Lecteur carte Lexar Multi-Card 3in1 USB 3.1", [("Neuf", "LEXAR-READER-3IN1", 350, None, 12, None)]),
    ("c-stand-support", "lighting-stands", "C-stand support", "C-stand support", [("Neuf", "CSTAND-SUPPORT", 1300, None, 4, None)]),
    ("stand-inox", "lighting-stands", "Stand inox", "Stand inox", [("Neuf", "STAND-INOX", 600, None, 8, None)]),
    ("fond-papier-272-11m-bleu", "studio-packs-photo", "Fond Papier 2,72 X 11m – Bleu", "Fond Papier 2,72 X 11m – Bleu", [("Neuf", "FOND-PAPIER-BLEU", 650, None, 6, None)]),
    ("fond-papier-272-11m-blanc", "studio-packs-photo", "Fond Papier 2,72 X 11m - Blanc", "Fond Papier 2,72 X 11m - Blanc", [("Neuf", "FOND-PAPIER-BLANC", 650, None, 6, None)]),
    ("fond-papier-272-11m-rouge", "studio-packs-photo", "Fond Papier 2,72 X 11m – Rouge", "Fond Papier 2,72 X 11m – Rouge", [("Neuf", "FOND-PAPIER-ROUGE", 650, None, 6, None)]),
    ("fond-papier-272-11m-jaune", "studio-packs-photo", "Fond Papier 2,72 X 11m – Jaune", "Fond Papier 2,72 X 11m – Jaune", [("Neuf", "FOND-PAPIER-JAUNE", 650, None, 6, None)]),
    ("fond-papier-272-11m-noir", "studio-packs-photo", "Fond Papier 2,72 X 11m – Noir", "Fond Papier 2,72 X 11m – Noir", [("Neuf", "FOND-PAPIER-NOIR", 650, None, 6, None)]),
    ("fond-papier-272-11m-vert", "studio-packs-photo", "Fond Papier 2,72 X 11m – Vert", "Fond Papier 2,72 X 11m – Vert", [("Neuf", "FOND-PAPIER-VERT", 650, None, 6, None)]),
    ("derouleur-fond-mural-3-fonds", "studio-packs-photo", "Dérouleur fond photo à fixations murales de 3 fonds", "Dérouleur fond photo à fixations murales de 3 fonds", [("Neuf", "DEROULEUR-3-FONDS", 950, None, 4, None)]),
    ("derouleur-fond-mural-4-fonds", "studio-packs-photo", "Dérouleur fond photo à fixations murales de 4 fonds", "Dérouleur fond photo à fixations murales de 4 fonds", [("Neuf", "DEROULEUR-4-FONDS", 1300, None, 3, None)]),
    ("mini-c-stand", "lighting-stands", "Mini C-stand", "Mini C-stand", [("Neuf", "MINI-CSTAND", 599, None, 6, None)]),
    ("lexar-professional-128-v90-uhs2", "memory-sd-cf", "Lexar 128GB V90 Professional 2000x UHS-II SDXC", "Lexar 128GB V90 Professional 2000x UHS-II SDXC", [("Neuf", "LEXAR-128-V90-UHS2", 1600, None, 8, None)]),
    ("sandisk-extreme-pro-128-v30", "memory-sd-cf", "SANDISK EXTREME PRO 128Go 200MB/s V30 U3", "SANDISK EXTREME PRO 128Go 200MB/s V30 U3", [("Neuf", "SANDISK-EP-128-V30", 400, None, 15, None)]),
    ("sandisk-extreme-pro-64-v30", "memory-sd-cf", "SANDISK EXTREME PRO 64Go 200MB/s V30", "SANDISK EXTREME PRO 64Go 200MB/s V30", [("Neuf", "SANDISK-EP-64-V30", 300, None, 18, None)]),
    ("sandisk-extreme-pro-sdxc-200-v30", "memory-sd-cf", "SANDISK EXTREME PRO SDXC UHS-I 200MB V30", "SANDISK EXTREME PRO SDXC UHS-I 200MB V30", [("Neuf", "SANDISK-EP-SDXC-200-V30", 750, None, 12, None)]),
    ("boya-by-bm6060", "audio-microphones-shotgun", "BOYA BY-BM6060 Shotgun Mic", "BOYA BY-BM6060 Shotgun Mic", [("Neuf", "BOYA-BM6060", 1100, None, 5, None)]),
    ("godox-iflash-im30", "lighting-led-panels", "Godox iflash im30", "Godox iflash im30", [("Neuf", "GODOX-IFLASH-IM30", 650, None, 10, None)]),
    ("dji-rs-4-pro-combo", "stabilization-gimbals", "DJI RS 4 Pro Combo", "DJI RS 4 Pro Combo", [("Combo", "DJI-RS4-PRO-COMBO", 12100, None, 4, None)]),
    ("dji-rs-4-pro", "stabilization-gimbals", "DJI RS 4 Pro", "DJI RS 4 Pro", [("Neuf", "DJI-RS4-PRO", 9700, None, 5, None)]),
    ("dji-rs-5-combo", "stabilization-gimbals", "DJI RS 5 Combo", "DJI RS 5 Combo", [("Combo", "DJI-RS5-COMBO", 7500, None, 4, None)]),
    ("dji-rs-4", "stabilization-gimbals", "DJI RS 4", "DJI RS 4", [("Neuf", "DJI-RS4", 5200, None, 6, None)]),
    ("dji-mic-3-2tx-1rx-case", "audio-wireless", "DJI Mic 3 (2 TX + 1 RX + Charging Case)", "DJI Mic 3 (2 TX + 1 RX + Charging Case)", [("2 TX + 1 RX + Case", "DJI-MIC3-2TX-CASE", 3400, None, 8, None)]),
    ("dji-mic-3-1tx-1rx", "audio-wireless", "DJI Mic 3 (1 TX + 1 RX)", "DJI Mic 3 (1 TX + 1 RX)", [("1 TX + 1 RX", "DJI-MIC3-1TX", 2300, None, 10, None)]),
    ("sac-lolobo-grand", "bags-backpacks", "Sac lolobo grand", "Sac lolobo grand", [("Neuf", "SAC-LOLOBO-GRAND", 850, None, 6, None)]),
    ("sac-camera", "bags-slings", "Sac camera", "Sac camera", [("Neuf", "SAC-CAMERA", 170, None, 10, None)]),
    ("tripod-candc-dc-999", "stabilization-tripods", "tripod candc dc-999 ( maximum height 1700mm - weight 1360g)", "tripod candc dc-999 ( maximum height 1700mm - weight 1360g)", [("Neuf", "CANDC-DC-999", 250, None, 8, None)]),
    ("tripod-candc-dc-6917", "stabilization-tripods", "tripod candc dc-6917 (maximum height 1700mm - load : 3kg)", "tripod candc dc-6917 (maximum height 1700mm - load : 3kg)", [("Neuf", "CANDC-DC-6917", 300, None, 7, None)]),
    ("tripod-candc-dc-6918", "stabilization-tripods", "tripod candc dc-6918 ( maximum height 1810mm - load 5kg - weight 1610g)", "tripod candc dc-6918 ( maximum height 1810mm - load 5kg - weight 1610g)", [("Neuf", "CANDC-DC-6918", 350, None, 6, None)]),
    ("feelworld-tp10", "monitors-on-camera", "FEELWORLD TP10 Portable 10 téléprompteur pliant", "FEELWORLD TP10 Portable 10 téléprompteur pliant", [("Neuf", "FEELWORLD-TP10", 1300, None, 4, None)]),
    ("kodak-gold-200-film-bundle", "studio-packs-photo", "Kodak Gold 200 35mm Film Bundle", "Kodak Gold 200 35mm Film Bundle", [("Neuf", "KODAK-GOLD200-BUNDLE", 200, None, 15, None)]),
    ("deity-v-mic-d3-pro", "audio-microphones-shotgun", "Deity V-MIC D3 PRO", "Deity V-MIC D3 PRO", [("Neuf", "DEITY-VMIC-D3PRO", 1600, None, 5, None)]),
    ("rode-videomic-go", "audio-microphones-shotgun", "Rode videomic go", "Rode videomic go", [("Neuf", "RODE-VM-GO", 750, None, 8, None)]),
    ("rode-wireless-go-ii-dual", "audio-wireless", "RØDE Wireless GO II (double émetteur) – Système micro sans fil", "RØDE Wireless GO II (double émetteur) – Système micro sans fil", [("2 TX + 1 RX", "RODE-WG2-DUAL", 3699, None, 4, None)]),
    ("rode-wireless-go-ii-single", "audio-wireless", "RØDE Wireless Go II Single Ultra-compact Dual-channel Wireless Microphone System", "RØDE Wireless Go II Single Ultra-compact Dual-channel Wireless Microphone System", [("1 TX + 1 RX", "RODE-WG2-SINGLE", 2699, None, 6, None)]),
    ("tamron-28-75-f28-g2-sony-fe", "lenses-zoom", "Tamron 28-75mm F2.8 Di III VXD G2 Sony FE", "Tamron 28-75mm F2.8 Di III VXD G2 Sony FE", [("Neuf", "TAMRON-2875-G2-FE", 8999, None, 2, None)]),
    ("feelworld-f7-plus", "monitors-on-camera", "FEELWORLD F7 Plus – Moniteur Tactile 7″ 4K", "FEELWORLD F7 Plus – Moniteur Tactile 7″ 4K", [("Neuf", "FEELWORLD-F7-PLUS", 2200, None, 4, None)]),
    ("zhiyun-torche-m20", "lighting-led-panels", "Zhiyun torche m20", "Zhiyun torche m20", [("Neuf", "ZHIYUN-TORCHE-M20", 1300, None, 6, None)]),
    ("vrig-fd-140-rgb", "lighting-led-panels", "Torche vrig fd-140 rgb fill light", "Torche vrig fd-140 rgb fill light", [("Neuf", "VRIG-FD140-RGB", 500, None, 10, None)]),
    ("canon-lc-e6", "power-chargers", "Canon LC-E6 Battery Charger for LP-E6 LP-E6N Li-Ion Batteries", "Canon LC-E6 Battery Charger for LP-E6 LP-E6N Li-Ion Batteries", [("Neuf", "CANON-LC-E6", 150, None, 12, None)]),
    ("canon-lc-e17", "power-chargers", "CHARGEUR DE BATTERIE CANON LC-E17", "CHARGEUR DE BATTERIE CANON LC-E17", [("Neuf", "CANON-LC-E17", 200, None, 10, None)]),
    ("canon-lc-e10", "power-chargers", "CHARGEUR DE BATTERIE CANON LC-E10", "CHARGEUR DE BATTERIE CANON LC-E10", [("Neuf", "CANON-LC-E10", 150, None, 10, None)]),
    ("sony-bc-qz1", "power-chargers", "Battery Charger for NP-FZ100 BC-QZ1", "Battery Charger for NP-FZ100 BC-QZ1", [("Neuf", "SONY-BC-QZ1", 200, None, 10, None)]),
    ("canon-lc-e8", "power-chargers", "Canon LC-E8 Battery Charger", "Canon LC-E8 Battery Charger", [("Neuf", "CANON-LC-E8", 150, None, 10, None)]),
    ("pisen-fz100-charging-box", "power-chargers", "PISEN FZ100 Battery Charging Box", "PISEN FZ100 Battery Charging Box", [("Neuf", "PISEN-FZ100-BOX", 450, None, 8, None)]),
    ("sony-np-f970", "batteries-camera", "Sony np-f970", "Sony np-f970", [("Neuf", "SONY-NP-F970", 550, None, 8, None)]),
    ("dji-mic-mini-2-combo", "audio-wireless", "Dji mic mini 2 (2tx + 1 rx + charging case)", "Dji mic mini 2 (2tx + 1 rx + charging case)", [("2 TX + 1 RX + Case", "DJI-MIC-MINI2-COMBO", 1400, None, 8, None)]),
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


async def ensure_categories(session: AsyncSession) -> dict[str, object]:
    category_ids: dict[str, object] = {}
    for index, (slug, (fr, ar, en, children)) in enumerate(CATEGORIES.items()):
        parent = await upsert_category(session, slug, (fr, ar, en), order=index)
        category_ids[slug] = parent.id
        for child_index, child_slug in enumerate(children):
            child_name = SUBCATEGORY_FR[child_slug]
            child = await upsert_category(session, child_slug, (child_name, child_name, child_name), parent.id, child_index)
            category_ids[child_slug] = child.id
    await session.flush()
    return category_ids


def seed_image_count(slug: str) -> int:
    return {
        "dji-osmo-nano-128gb": 1,
        "dji-osmo-mobile-7": 5,
        "dji-osmo-mobile-7p": 2,
        "dji-osmo-mobile-8": 3,
        "dji-action-6-standard": 3,
        "dji-action-6-adventure-combo": 3,
        "dji-rs4-mini": 3,
        "dji-rs5": 3,
    }.get(slug, 4)


async def find_product_by_offer_sku(session: AsyncSession, sku: str) -> Product | None:
    offer = await session.scalar(select(ProductOffer).where(ProductOffer.sku == sku))
    if offer is None:
        return None
    return await session.scalar(select(Product).where(Product.id == offer.product_id))


async def upsert_product_offers(
    session: AsyncSession,
    product_id: object,
    slug: str,
    offers: list,
) -> None:
    for offer_index, (label, sku, price, compare_at, stock, badge) in enumerate(offers):
        existing = await session.scalar(select(ProductOffer).where(ProductOffer.sku == sku))
        if existing is not None:
            if existing.product_id != product_id:
                print(
                    f"Skip offer {sku} for {slug}: SKU already used by product {existing.product_id}",
                    flush=True,
                )
                continue
            existing.label = label
            existing.price = Decimal(str(price))
            existing.compare_at_price = Decimal(str(compare_at)) if compare_at else None
            existing.stock = stock
            existing.is_default = offer_index == 0
            existing.badge = badge
            existing.sort_order = offer_index
            continue

        session.add(
            ProductOffer(
                product_id=product_id,
                sku=sku,
                label=label,
                price=Decimal(str(price)),
                compare_at_price=Decimal(str(compare_at)) if compare_at else None,
                stock=stock,
                is_default=offer_index == 0,
                badge=badge,
                sort_order=offer_index,
            )
        )


async def ensure_product_translations(
    session: AsyncSession,
    product_id: object,
    slug: str,
    name: str,
    headline: str,
) -> None:
    for locale in ("fr", "ar", "en"):
        description = PRODUCT_DESCRIPTIONS.get(slug, f"{headline}. Pensé pour les créateurs exigeants au Maroc.")
        translation = await session.scalar(
            select(ProductTranslation).where(
                ProductTranslation.product_id == product_id,
                ProductTranslation.locale == locale,
            )
        )
        if translation is None:
            session.add(
                ProductTranslation(
                    product_id=product_id,
                    locale=locale,
                    name=name,
                    headline=headline,
                    subheadline="Équipement professionnel, original et garanti.",
                    description=description,
                    short_description=headline,
                    meta_title=name,
                    meta_description=headline,
                )
            )
            continue
        translation.name = name
        translation.headline = headline
        translation.subheadline = "Équipement professionnel, original et garanti."
        translation.description = description
        translation.short_description = headline
        translation.meta_title = name
        translation.meta_description = headline


async def ensure_product_images(session: AsyncSession, product_id: object, slug: str, name: str) -> None:
    image_count = await session.scalar(
        select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product_id)
    )
    if image_count and image_count > 0:
        return

    if slug in PRODUCT_IMAGES:
        session.add(
            ProductImage(
                product_id=product_id,
                url=PRODUCT_IMAGES[slug],
                alt_text=name,
                sort_order=0,
                is_lifestyle=False,
            )
        )
        return

    for image_index in range(seed_image_count(slug)):
        session.add(
            ProductImage(
                product_id=product_id,
                url=f"/media/placeholders/{slug}-{image_index}.webp",
                alt_text=name,
                sort_order=image_index,
                is_lifestyle=image_index == seed_image_count(slug) - 1,
            )
        )


async def ensure_product_specs(session: AsyncSession, product_id: object, slug: str) -> None:
    spec_count = await session.scalar(
        select(func.count()).select_from(ProductSpec).where(ProductSpec.product_id == product_id)
    )
    if spec_count and spec_count > 0:
        return

    for sort_order, (spec_key, spec_value) in enumerate(PRODUCT_SPECS.get(slug, DEFAULT_PRODUCT_SPECS)):
        session.add(
            ProductSpec(
                product_id=product_id,
                locale="fr",
                spec_key=spec_key,
                spec_value=spec_value,
                sort_order=sort_order,
            )
        )


async def apply_seed_product_data(
    session: AsyncSession,
    product: Product,
    index: int,
    slug: str,
    category_slug: str,
    name: str,
    headline: str,
    offers: list,
    category_ids: dict[str, object],
) -> None:
    product.category_id = category_ids[category_slug]
    product.is_active = True
    product.sort_order = index
    await ensure_product_translations(session, product.id, slug, name, headline)
    await ensure_product_images(session, product.id, slug, name)
    await ensure_product_specs(session, product.id, slug)
    await upsert_product_offers(session, product.id, slug, offers)


async def create_seed_product(
    session: AsyncSession,
    index: int,
    slug: str,
    category_slug: str,
    name: str,
    headline: str,
    offers: list,
    category_ids: dict[str, object],
) -> Product:
    product = Product(
        category_id=category_ids[category_slug],
        slug=slug,
        rating=Decimal("4.8"),
        review_count=24 + index * 7,
        is_featured=index < 6,
        sort_order=index,
        is_active=True,
    )
    session.add(product)
    await session.flush()
    await apply_seed_product_data(session, product, index, slug, category_slug, name, headline, offers, category_ids)
    return product


async def sync_missing_seed_products(session: AsyncSession) -> int:
    category_ids = await ensure_categories(session)
    added = 0
    reconciled = 0

    for index, (slug, category_slug, name, headline, offers) in enumerate(PRODUCTS):
        if slug in REMOVED_PRODUCT_SLUGS:
            continue

        with session.no_autoflush:
            product = await session.scalar(select(Product).where(Product.slug == slug))
            if product is None:
                for offer in offers:
                    product = await find_product_by_offer_sku(session, offer[1])
                    if product is not None:
                        break

        if product is not None:
            slug_owner = await session.scalar(select(Product).where(Product.slug == slug))
            if slug_owner is not None and slug_owner.id != product.id:
                print(f"Skip {slug}: slug already belongs to another product", flush=True)
                continue

            if product.slug != slug:
                print(f"Reconciled product by SKU: {product.slug} -> {slug}", flush=True)
                product.slug = slug
                reconciled += 1

            await apply_seed_product_data(
                session, product, index, slug, category_slug, name, headline, offers, category_ids
            )
            continue

        with session.no_autoflush:
            await create_seed_product(
                session, index, slug, category_slug, name, headline, offers, category_ids
            )
        added += 1
        print(f"Added missing seed product: {slug}", flush=True)

    if added or reconciled:
        await session.flush()
    if reconciled:
        print(f"Light bootstrap: reconciled {reconciled} products by SKU", flush=True)
    return added


def copy_seed_media() -> None:
    source_dir = Path(__file__).resolve().parent / "assets" / "placeholders"
    if not source_dir.is_dir():
        return
    target_dir = Path(settings.media_root) / "placeholders"
    target_dir.mkdir(parents=True, exist_ok=True)
    for asset in source_dir.iterdir():
        if asset.is_file():
            shutil.copy2(asset, target_dir / asset.name)


async def sync_seed_product(session: AsyncSession, product: Product, name: str, headline: str, offers: list) -> None:
    await ensure_product_translations(session, product.id, product.slug, name, headline)

    existing_offers = await session.scalars(select(ProductOffer).where(ProductOffer.product_id == product.id))
    seed_skus = {offer[1] for offer in offers}
    for offer in existing_offers:
        if offer.sku not in seed_skus:
            await session.delete(offer)
    await session.flush()
    await upsert_product_offers(session, product.id, product.slug, offers)

    if product.slug in PRODUCT_IMAGES:
        existing_images = await session.scalars(select(ProductImage).where(ProductImage.product_id == product.id))
        for image in existing_images:
            await session.delete(image)
        await session.flush()
        image_url = PRODUCT_IMAGES[product.slug]
        session.add(ProductImage(product_id=product.id, url=image_url, alt_text=name, sort_order=0, is_lifestyle=False))


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


async def ensure_admin(session: AsyncSession) -> None:
    admin = await session.scalar(select(Admin).where(Admin.email == settings.admin_email))
    if admin is None:
        session.add(
            Admin(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                full_name="Moviecam Admin",
            )
        )
    else:
        admin.password_hash = hash_password(settings.admin_password)
        admin.is_active = True


async def seed(session: AsyncSession) -> None:
    product_count = int(await session.scalar(select(func.count()).select_from(Product)) or 0)
    force_sync = os.getenv("SEED_FORCE_SYNC", "").lower() in {"1", "true", "yes"}
    light_bootstrap = product_count > 0 and not force_sync

    if light_bootstrap:
        print(f"Light bootstrap: {product_count} products already seeded, skipping full sync", flush=True)
        await deactivate_removed_products(session)
        added = await sync_missing_seed_products(session)
        if added:
            print(f"Light bootstrap: added {added} missing products", flush=True)
        await ensure_admin(session)
        return

    copy_seed_media()
    await deactivate_removed_products(session)
    await ensure_admin(session)

    category_ids = await ensure_categories(session)

    product_ids: dict[str, object] = {}
    for index, (slug, category_slug, name, headline, offers) in enumerate(PRODUCTS):
        product = await session.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            product = await create_seed_product(session, index, slug, category_slug, name, headline, offers, category_ids)
        elif slug in PRODUCT_IMAGES:
            await sync_seed_product(session, product, name, headline, offers)
        product_ids[slug] = product.id
    await session.flush()

    for source, targets in {"sony-a7iv": ["sandisk-extreme-pro-128-v30", "sony-np-fz100", "sony-fe-50mm-f18"], "sony-fx3": ["sandisk-extreme-pro-128-v30", "sony-np-fz100", "sony-a7iv", "sony-fe-24-70-f28-gm"], "sony-a7iii": ["sandisk-extreme-pro-128-v30", "sony-np-fz100", "sony-a7iv", "sony-fe-50mm-f18"], "sony-fe-50mm-f18": ["sony-a7iv", "sony-a7iii"], "sony-fe-24-70-f4": ["sony-a7iii", "sandisk-extreme-pro-128-v30"], "sony-fe-24-70-f28-gm": ["sony-a7iv", "sony-fx3", "sandisk-extreme-pro-128-v30"], "sony-np-fz100": ["sony-a7iv", "sony-fx3", "sony-fx30"], "sony-fx30": ["sony-np-fz100", "sandisk-extreme-pro-128-v30", "sony-fe-24-70-f28-gm"], "dji-osmo-pocket-4-creator-combo": ["sandisk-extreme-pro-128-v30", "dji-osmo-pocket-4-standard", "dji-mic-mini-2-combo"], "dji-osmo-pocket-4-standard": ["sandisk-extreme-pro-128-v30", "dji-osmo-pocket-4-creator-combo", "dji-mic-mini-2-combo"], "godox-v1-sony": ["godox-ak-r22", "godox-lc500r-mini"], "godox-ak-r22": ["godox-v1-sony", "godox-lc500r-mini"], "godox-lc500r-mini": ["godox-v1-sony", "godox-ak-r22"], "dji-mic-mini-2-combo": ["sandisk-extreme-pro-128-v30", "rode-videomic-go"], "dji-rs4-mini": ["sony-np-fz100", "sandisk-extreme-pro-128-v30", "dji-mic-mini-2-combo"], "dji-rs5": ["sony-np-fz100", "sandisk-extreme-pro-128-v30", "dji-rs4-mini"], "dji-osmo-mobile-7": ["dji-osmo-pocket-3-standard", "dji-mic-mini-2-combo"], "dji-osmo-mobile-7p": ["dji-osmo-mobile-7", "dji-osmo-pocket-3-standard"], "dji-osmo-mobile-8": ["dji-osmo-mobile-7p", "dji-osmo-pocket-3-standard"], "dji-osmo-pocket-3-standard": ["sandisk-extreme-pro-128-v30", "dji-mic-mini-2-combo"], "dji-osmo-pocket-3-creator-combo": ["sandisk-extreme-pro-128-v30", "dji-osmo-pocket-3-standard", "dji-mic-mini-2-combo"], "dji-osmo-nano-128gb": ["sandisk-extreme-pro-128-v30", "dji-osmo-pocket-3-standard"], "dji-action-6-standard": ["sandisk-extreme-pro-128-v30", "dji-osmo-nano-128gb", "dji-mic-mini-2-combo"], "dji-action-6-adventure-combo": ["dji-action-6-standard", "sandisk-extreme-pro-128-v30", "dji-mic-mini-2-combo"], "dji-rs-4-pro-combo": ["dji-rs-4-pro", "dji-mic-3-2tx-1rx-case", "sandisk-extreme-pro-128-v30"], "dji-rs-4-pro": ["dji-rs-4-pro-combo", "dji-rs-4", "dji-mic-3-1tx-1rx"], "dji-rs-5-combo": ["dji-rs5", "dji-rs-4-pro", "dji-mic-3-2tx-1rx-case"], "dji-rs-4": ["dji-rs-4-pro", "dji-rs4-mini", "dji-mic-3-1tx-1rx"], "dji-mic-3-2tx-1rx-case": ["dji-mic-3-1tx-1rx", "dji-mic-mini-2-combo", "sandisk-extreme-pro-128-v30"], "dji-mic-3-1tx-1rx": ["dji-mic-3-2tx-1rx-case", "dji-mic-mini-2-combo", "rode-videomic-go"], "sac-lolobo-grand": ["sac-camera", "sony-a7iv", "tripod-candc-dc-6918"], "sac-camera": ["sac-lolobo-grand", "sony-a7iii"], "tripod-candc-dc-999": ["tripod-candc-dc-6917", "tripod-candc-dc-6918", "sac-camera"], "tripod-candc-dc-6917": ["tripod-candc-dc-6918", "tripod-candc-dc-999"], "tripod-candc-dc-6918": ["tripod-candc-dc-6917", "dji-rs-4-pro"], "feelworld-tp10": ["feelworld-f5-prox", "sony-a7iv"], "kodak-gold-200-film-bundle": ["sony-a7iii", "sony-fe-50mm-f18"], "deity-v-mic-d3-pro": ["rode-videomic-go", "rode-videomic-go"], "rode-videomic-go": ["deity-v-mic-d3-pro", "rode-videomic-go"], "rode-wireless-go-ii-dual": ["rode-wireless-go-ii-single", "dji-mic-mini-2-combo"], "rode-wireless-go-ii-single": ["rode-wireless-go-ii-dual", "dji-mic-mini-2-combo"], "tamron-28-75-f28-g2-sony-fe": ["sony-a7iv", "sony-fe-24-70-f28-gm", "kf-concept-nano-b-nd2-400"]}.items():
        for priority, target in enumerate(targets):
            exists = await session.scalar(select(ProductCrossSell).where(ProductCrossSell.product_id == product_ids[source], ProductCrossSell.cross_sell_product_id == product_ids[target]))
            if exists is None:
                session.add(ProductCrossSell(product_id=product_ids[source], cross_sell_product_id=product_ids[target], priority=priority))


async def main() -> None:
    print("Running seed...", flush=True)
    async with async_session() as session:
        async with session.begin():
            await seed(session)
    print("Seed complete.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
