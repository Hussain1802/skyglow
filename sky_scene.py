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
    5: "Weak trace",
    6: "Normally invisible",
    7: "Not visible",
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

# A long-exposure photo shows far more contrast than a person sees. These
# values were tuned by comparing all nine results together.
SKY_DETAIL_LEFT = {
    1: 1.00,
    2: 0.78,
    3: 0.56,
    4: 0.30,
    5: 0.06,
    6: 0.020,
    7: 0.004,
    8: 0.000,
    9: 0.000,
}

# Higher classes require a brighter point before it is kept as a visible star.
STAR_THRESHOLDS = {
    1: 0,
    2: 4,
    3: 8,
    4: 13,
    5: 18,
    6: 24,
    7: 32,
    8: 42,
    9: 52,
}


@lru_cache(maxsize=1)
def load_source_photo():
    """Load a web-sized copy of the real ESO panorama."""
    with Image.open(PHOTO_PATH) as source:
        photo = source.convert("RGB")

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

    # This follows the horizon in this one fixed photograph. It is deliberately
    # simple: SkyGlow is not pretending to be an image-segmentation program.
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
    draw.polygon([(0, 0), (width, 0), *reversed(horizon)], fill=255)

    # One pixel of feathering avoids a jagged edge along the mountain ridge.
    return mask.filter(ImageFilter.GaussianBlur(radius=1))


def simulate_skyglow(photo, level):
    """Lower celestial contrast and add sky glow above the fixed horizon."""
    width, height = SCENE_SIZE
    pollution = (level - 1) / 8
    if pollution == 0:
        return photo.copy()

    original = np.asarray(photo, dtype=np.float32)
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    x = np.linspace(-1, 1, width, dtype=np.float32)[None, :]

    # Make a clean sky background. It is darker overhead and warmer near the
    # horizon, with a broad glow dome suggesting a town in the distance.
    horizon_amount = np.clip((y - 0.05) / 0.72, 0, 1) ** 2.1
    city_dome = np.exp(-((x / 0.62) ** 2 + ((y - 0.73) / 0.30) ** 2))

    top_colour = np.array([38, 42, 53], dtype=np.float32)
    horizon_colour = np.array([165, 112, 84], dtype=np.float32)
    sky_background = (
        top_colour[None, None, :] * (1 - horizon_amount[:, :, None])
        + horizon_colour[None, None, :] * horizon_amount[:, :, None]
    )
    sky_background = np.broadcast_to(
        sky_background,
        (height, width, 3),
    ).copy()
    sky_background += city_dome[:, :, None] * (28 * pollution)

    # Whole-sky contrast falls sharply by class 5. This removes the broad
    # Milky Way band as well as its finer texture.
    detail_left = SKY_DETAIL_LEFT[level]
    faded_sky = sky_background + (original - sky_background) * detail_left

    # Bring back only compact, bright stars. The blurred copy is used only to
    # find small points; it is never shown to the user.
    local_background = np.asarray(
        photo.filter(ImageFilter.GaussianBlur(radius=1.4)),
        dtype=np.float32,
    )
    bright_points = np.maximum(original - local_background, 0)
    point_brightness = (
        0.2126 * bright_points[:, :, 0]
        + 0.7152 * bright_points[:, :, 1]
        + 0.0722 * bright_points[:, :, 2]
    )
    threshold = STAR_THRESHOLDS[level]
    star_gate = np.clip((point_brightness - threshold) / 18, 0, 1)
    star_strength = 0.78 - (0.32 * pollution)
    faded_sky += (
        bright_points
        * star_gate[:, :, None]
        * star_strength
        * (1 - detail_left)
    )

    # The land is copied back pixel-for-pixel. Only the sky mask receives the
    # simulated change.
    sky_mask = np.asarray(make_sky_mask(), dtype=np.float32)[:, :, None] / 255
    combined = faded_sky * sky_mask + original * (1 - sky_mask)
    return Image.fromarray(np.uint8(np.clip(combined, 0, 255)), "RGB")


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
    image = simulate_skyglow(source, level)
    image = add_photo_credit(image)

    metrics = {
        "visible_stars": VISIBLE_STAR_ESTIMATES[level],
        "limiting_magnitude": LIMITING_MAGNITUDES[level],
        "milky_way": MILKY_WAY_LABELS[level],
        "class_name": BORTLE_NAMES[level],
    }
    return image, metrics
