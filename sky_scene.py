from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


PHOTO_PATH = Path(__file__).parent / "assets" / "paranal-panorama.jpg"
SCENE_SIZE = (1600, 800)

# These are useful visual guideposts, not promises about a particular address.
LIMITING_MAGNITUDES = {
    1: 7.6,
    2: 7.1,
    3: 6.6,
    4: 6.2,
    5: 5.8,
    6: 5.3,
    7: 4.8,
    8: 4.3,
    9: 3.8,
}

VISIBLE_STAR_ESTIMATES = {
    1: 2600,
    2: 2200,
    3: 1700,
    4: 1200,
    5: 700,
    6: 350,
    7: 170,
    8: 80,
    9: 30,
}

MILKY_WAY_LABELS = {
    1: "Unmissable",
    2: "Clearly visible",
    3: "Detailed",
    4: "Visible",
    5: "Faint",
    6: "Barely visible",
    7: "Lost in skyglow",
    8: "Not visible",
    9: "Not visible",
}

BORTLE_NAMES = {
    1: "Excellent dark sky",
    2: "Typical dark site",
    3: "Rural sky",
    4: "Rural–suburban transition",
    5: "Suburban sky",
    6: "Bright suburban sky",
    7: "Suburban–urban transition",
    8: "City sky",
    9: "Inner-city sky",
}


@lru_cache(maxsize=1)
def load_source_photo():
    """Load a web-sized copy of the real ESO panorama."""
    with Image.open(PHOTO_PATH) as source:
        photo = source.convert("RGB")

    # The ESO image is already close to 2:1, so this only trims a few pixels.
    wanted_ratio = SCENE_SIZE[0] / SCENE_SIZE[1]
    current_ratio = photo.width / photo.height

    if current_ratio > wanted_ratio:
        new_width = int(photo.height * wanted_ratio)
        left = (photo.width - new_width) // 2
        photo = photo.crop((left, 0, left + new_width, photo.height))
    else:
        new_height = int(photo.width / wanted_ratio)
        top = (photo.height - new_height) // 2
        photo = photo.crop((0, top, photo.width, top + new_height))

    return photo.resize(SCENE_SIZE, Image.Resampling.LANCZOS)


def make_haze_layer(level):
    """Build warm atmospheric glow, strongest near the horizon."""
    width, height = SCENE_SIZE
    pollution = (level - 1) / 8

    y = np.linspace(0, 1, height)[:, None]
    horizon_glow = np.exp(-((y - 0.66) / 0.24) ** 2)
    upper_haze = 0.20 + 0.30 * y
    strength = (0.18 * upper_haze + 0.70 * horizon_glow) * pollution**1.15

    # The mask fades before reaching the ground, so the landscape stays solid.
    sky_mask = np.clip((0.83 - y) / 0.14, 0, 1)
    strength *= sky_mask
    strength = np.repeat(strength, width, axis=1)

    haze = np.zeros((height, width, 4), dtype=np.uint8)
    haze[:, :, 0] = 226
    haze[:, :, 1] = 132
    haze[:, :, 2] = 72
    haze[:, :, 3] = np.uint8(np.clip(strength * 255, 0, 225))

    return Image.fromarray(haze, "RGBA")


def wash_out_faint_detail(photo, level):
    """Reduce the contrast that makes faint stars and dust lanes visible."""
    pollution = (level - 1) / 8
    if pollution == 0:
        return photo.copy()

    # Faint stars live mostly in the small, sharp differences between pixels.
    # Mixing toward a soft copy removes those details without drawing fake stars.
    soft_radius = 3 + 23 * pollution
    soft_photo = photo.filter(ImageFilter.GaussianBlur(radius=soft_radius))
    mixed = Image.blend(photo, soft_photo, 0.20 + 0.74 * pollution)

    contrast = 1.0 - 0.42 * pollution
    saturation = 1.0 - 0.28 * pollution
    mixed = ImageEnhance.Contrast(mixed).enhance(contrast)
    mixed = ImageEnhance.Color(mixed).enhance(saturation)

    return mixed


def add_photo_credit(image):
    """Keep the required image credit attached to downloaded scenes."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    credit = "Photo: ESO/P. Horálek · Skyglow effect simulated"

    box = draw.textbbox((0, 0), credit)
    text_width = box[2] - box[0]
    x = image.width - text_width - 18
    y = image.height - 28

    draw.rounded_rectangle(
        (x - 8, y - 5, image.width - 8, image.height - 7),
        radius=5,
        fill=(2, 5, 12, 150),
    )
    draw.text((x, y), credit, fill=(235, 239, 247, 220))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def render_sky(level):
    """Apply the selected light-pollution effect to the real source photo."""
    source = load_source_photo()
    image = wash_out_faint_detail(source, level)
    image = Image.alpha_composite(
        image.convert("RGBA"),
        make_haze_layer(level),
    ).convert("RGB")

    # A slight lift mimics the loss of a truly black background in bright skies.
    pollution = (level - 1) / 8
    image = ImageEnhance.Brightness(image).enhance(1.0 + 0.10 * pollution)
    image = add_photo_credit(image)

    metrics = {
        "visible_stars": VISIBLE_STAR_ESTIMATES[level],
        "limiting_magnitude": LIMITING_MAGNITUDES[level],
        "milky_way": MILKY_WAY_LABELS[level],
        "class_name": BORTLE_NAMES[level],
    }
    return image, metrics
