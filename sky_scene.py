from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


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
    8: "Invisible unaided",
    9: "Invisible unaided",
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


@lru_cache(maxsize=1)
def make_sky_mask():
    """Separate the photographed sky from the foreground landscape."""
    width, height = SCENE_SIZE

    # This horizon follows the fixed Paranal panorama. Keeping it explicit is
    # simpler and more reliable than pretending this is general image segmentation.
    horizon = [
        (0, 588),
        (80, 590),
        (160, 594),
        (240, 590),
        (320, 595),
        (400, 601),
        (480, 600),
        (560, 602),
        (640, 602),
        (680, 599),
        (700, 598),
        (720, 594),
        (740, 586),
        (760, 576),
        (780, 567),
        (800, 564),
        (820, 574),
        (840, 582),
        (860, 592),
        (880, 600),
        (900, 604),
        (920, 610),
        (940, 605),
        (960, 604),
        (1040, 599),
        (1120, 610),
        (1200, 614),
        (1280, 624),
        (1360, 623),
        (1440, 617),
        (1520, 613),
        (1600, 610),
    ]

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(
        [(0, 0), (width, 0), *reversed(horizon)],
        fill=255,
    )

    # A small feather avoids a hard cut exactly along the mountain ridge.
    return mask.filter(ImageFilter.GaussianBlur(radius=2))


def fade_compact_stars(photo, level):
    """Dim small bright points while leaving broad structures sharp."""
    pollution = (level - 1) / 8
    if pollution == 0:
        return photo.copy()

    original = np.asarray(photo, dtype=np.float32)
    local_background = np.asarray(
        photo.filter(ImageFilter.GaussianBlur(radius=1.2)),
        dtype=np.float32,
    )

    positive_detail = np.maximum(original - local_background, 0)
    detail_brightness = (
        0.2126 * positive_detail[:, :, 0]
        + 0.7152 * positive_detail[:, :, 1]
        + 0.0722 * positive_detail[:, :, 2]
    )

    # Only compact bright points are affected. Large Milky Way structure and
    # mountain edges do not meet this threshold strongly enough to be smeared.
    star_mask = np.clip((detail_brightness - 1.5) / 13.0, 0, 1)
    removal = positive_detail * star_mask[:, :, None] * (0.88 * pollution)
    faded = np.clip(original - removal, 0, 255)

    return Image.fromarray(faded.astype(np.uint8), "RGB")


def add_skyglow(photo, level):
    """Wash out sky contrast with light, without blurring the photograph."""
    width, height = SCENE_SIZE
    pollution = (level - 1) / 8
    if pollution == 0:
        return photo.copy()

    y = np.linspace(0, 1, height)[:, None]
    x = np.linspace(-1, 1, width)[None, :]

    horizon_glow = np.exp(-((y - 0.72) / 0.25) ** 2)
    city_dome = np.exp(-((x / 0.56) ** 2 + ((y - 0.80) / 0.34) ** 2))
    upper_haze = 0.14 + 0.18 * y

    strength = upper_haze + 0.44 * horizon_glow + 0.24 * city_dome
    strength *= pollution**1.30

    # Severe urban skies lose contrast across the whole sky, not only at the
    # horizon. The cubic term stays small in suburbs and rises sharply at 8–9.
    strength += 0.45 * pollution**3
    strength = np.clip(strength, 0, 0.90)

    original = np.asarray(photo, dtype=np.float32) / 255

    # Urban LEDs are often neutral while older lighting is warmer. This muted
    # tone avoids turning every city sky into a flat orange wall.
    haze_color = np.zeros_like(original)
    haze_color[:, :, 0] = 0.64 + 0.13 * horizon_glow
    haze_color[:, :, 1] = 0.52 + 0.05 * horizon_glow
    haze_color[:, :, 2] = 0.46

    washed_sky = (
        original * (1 - strength[:, :, None])
        + haze_color * strength[:, :, None]
    )

    washed_sky = Image.fromarray(
        np.uint8(np.clip(washed_sky * 255, 0, 255)),
        "RGB",
    )

    # The foreground comes straight from the source photo. Only the feathered
    # strip along the true horizon blends with the processed sky.
    return Image.composite(
        washed_sky,
        photo,
        make_sky_mask(),
    )


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
    faded_stars = fade_compact_stars(source, level)
    image = add_skyglow(faded_stars, level)
    image = add_photo_credit(image)

    metrics = {
        "visible_stars": VISIBLE_STAR_ESTIMATES[level],
        "limiting_magnitude": LIMITING_MAGNITUDES[level],
        "milky_way": MILKY_WAY_LABELS[level],
        "class_name": BORTLE_NAMES[level],
    }
    return image, metrics
