from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH = 1200
HEIGHT = 720

# These values are deliberately approximate. SkyGlow is a visual explanation,
# not a calibrated sky-brightness model.
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

MILKY_WAY_LABELS = {
    1: "Striking",
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

# A few recognizable stars make the scene feel less anonymous. Their positions
# are arranged for this landscape rather than copied from a planetarium view.
NAMED_STARS = [
    ("Vega", 0.22, 0.18, 0.0, "blue"),
    ("Deneb", 0.36, 0.10, 1.3, "white"),
    ("Altair", 0.43, 0.34, 0.8, "white"),
    ("Betelgeuse", 0.72, 0.25, 0.5, "orange"),
    ("Bellatrix", 0.78, 0.27, 1.6, "blue"),
    ("Alnitak", 0.75, 0.38, 1.7, "blue"),
    ("Alnilam", 0.78, 0.39, 1.7, "blue"),
    ("Mintaka", 0.81, 0.40, 2.2, "blue"),
    ("Rigel", 0.83, 0.52, 0.1, "blue"),
    ("Saiph", 0.73, 0.51, 2.1, "blue"),
]

CONSTELLATION_LINES = [
    ("Vega", "Deneb"),
    ("Deneb", "Altair"),
    ("Altair", "Vega"),
    ("Betelgeuse", "Bellatrix"),
    ("Betelgeuse", "Alnitak"),
    ("Bellatrix", "Mintaka"),
    ("Alnitak", "Alnilam"),
    ("Alnilam", "Mintaka"),
    ("Alnitak", "Saiph"),
    ("Mintaka", "Rigel"),
    ("Saiph", "Rigel"),
]


@lru_cache(maxsize=1)
def make_star_catalogue():
    """Create one repeatable field of stars for every render."""
    random = np.random.default_rng(1802)
    star_count = 5200

    x = random.uniform(0.015, 0.985, star_count)
    y = random.uniform(0.015, 0.78, star_count)

    # There are many more faint stars than bright ones.
    magnitudes = 1.1 + 6.7 * random.random(star_count) ** 0.25
    colors = random.choice(
        ["blue", "white", "warm"],
        size=star_count,
        p=[0.18, 0.62, 0.20],
    )
    twinkle = random.uniform(0.78, 1.0, star_count)

    return x, y, magnitudes, colors, twinkle


def make_sky_background(level):
    """Paint the blue-black sky and the warm glow near the horizon."""
    y = np.linspace(0, 1, HEIGHT)[:, None]

    pollution = (level - 1) / 8
    top = np.array([3, 7, 20], dtype=float)
    horizon_dark = np.array([12, 22, 42], dtype=float)
    horizon_city = np.array([132, 84, 53], dtype=float)
    horizon = horizon_dark * (1 - pollution) + horizon_city * pollution

    vertical_blend = np.clip((y - 0.18) / 0.82, 0, 1) ** 2.3
    sky = top[None, None, :] * (1 - vertical_blend[:, :, None])
    sky += horizon[None, None, :] * vertical_blend[:, :, None]
    sky = np.repeat(sky, WIDTH, axis=1)

    # A broad dome makes city glow feel less like a flat color gradient.
    x = np.linspace(-1, 1, WIDTH)[None, :]
    dome = np.exp(-((x / 0.56) ** 2 + ((y - 1.03) / 0.38) ** 2))
    glow_color = np.array([235, 138, 62], dtype=float)
    sky += dome[:, :, None] * glow_color * (pollution**1.4) * 0.42

    return Image.fromarray(np.uint8(np.clip(sky, 0, 255)), "RGB")


def add_milky_way(image, level):
    """Add a soft, irregular Milky Way band that fades with skyglow."""
    strength = np.clip(1.12 - (level - 1) / 5.4, 0, 1)
    if strength <= 0:
        return image

    random = np.random.default_rng(42)
    small_noise = random.random((90, 150))
    noise_image = Image.fromarray(np.uint8(small_noise * 255))
    noise_image = noise_image.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC)
    noise = np.asarray(noise_image, dtype=float) / 255

    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    center_line = HEIGHT * (0.68 - 0.72 * xx / WIDTH)
    center_line += 25 * np.sin(xx / WIDTH * np.pi * 2)
    distance = np.abs(yy - center_line)

    broad_band = np.exp(-((distance / 115) ** 2))
    bright_core = np.exp(-((distance / 40) ** 2))
    texture = 0.42 + 0.58 * noise
    mask = np.clip((broad_band * 0.36 + bright_core * 0.34) * texture, 0, 1)
    mask *= strength
    mask *= np.clip((HEIGHT * 0.80 - yy) / 110, 0, 1)

    cloud_color = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    cloud_color[:, :, 0] = 132
    cloud_color[:, :, 1] = 151
    cloud_color[:, :, 2] = 188
    cloud_color[:, :, 3] = np.uint8(mask * 118)

    layer = Image.fromarray(cloud_color, "RGBA").filter(
        ImageFilter.GaussianBlur(radius=3)
    )
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_stars(image, level):
    """Draw every star bright enough to survive the selected skyglow."""
    x, y, magnitudes, colors, twinkle = make_star_catalogue()
    limiting_magnitude = LIMITING_MAGNITUDES[level]
    visible = magnitudes <= limiting_magnitude

    star_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(star_layer)

    palette = {
        "blue": (192, 217, 255),
        "white": (245, 247, 255),
        "warm": (255, 225, 185),
    }

    visible_indices = np.flatnonzero(visible)
    for index in visible_indices:
        px = int(x[index] * WIDTH)
        py = int(y[index] * HEIGHT)
        magnitude = magnitudes[index]

        brightness = (limiting_magnitude - magnitude + 0.7) / 6.5
        brightness = np.clip(brightness, 0.10, 1.0) * twinkle[index]
        radius = 0.45 + 2.0 * brightness**1.8
        color = palette[colors[index]]
        alpha = int(80 + 175 * brightness)

        if radius > 1.4:
            glow_radius = radius * 3.2
            glow_color = (*color, int(alpha * 0.13))
            draw.ellipse(
                (
                    px - glow_radius,
                    py - glow_radius,
                    px + glow_radius,
                    py + glow_radius,
                ),
                fill=glow_color,
            )

        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=(*color, alpha),
        )

    star_layer = star_layer.filter(ImageFilter.GaussianBlur(radius=0.25))
    image = Image.alpha_composite(image.convert("RGBA"), star_layer)
    return image.convert("RGB"), int(visible.sum())


def add_named_stars(image, level, show_lines, show_labels):
    """Add the small Orion and Summer Triangle overlays."""
    limiting_magnitude = LIMITING_MAGNITUDES[level]
    positions = {
        name: (int(x * WIDTH), int(y * HEIGHT))
        for name, x, y, magnitude, color in NAMED_STARS
        if magnitude <= limiting_magnitude
    }

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if show_lines:
        for start, end in CONSTELLATION_LINES:
            if start in positions and end in positions:
                draw.line(
                    (positions[start], positions[end]),
                    fill=(128, 169, 210, 105),
                    width=2,
                )

    star_colors = {
        "blue": (194, 222, 255),
        "white": (255, 255, 246),
        "orange": (255, 188, 126),
    }
    for name, x, y, magnitude, color in NAMED_STARS:
        if magnitude > limiting_magnitude:
            continue

        px, py = int(x * WIDTH), int(y * HEIGHT)
        radius = max(2.0, 4.4 - magnitude * 0.7)
        draw.ellipse(
            (px - radius * 3, py - radius * 3, px + radius * 3, py + radius * 3),
            fill=(*star_colors[color], 35),
        )
        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=(*star_colors[color], 255),
        )

        if show_labels and name in {"Vega", "Deneb", "Altair", "Betelgeuse", "Rigel"}:
            draw.text(
                (px + 9, py - 13),
                name,
                fill=(224, 233, 247, 205),
                stroke_width=2,
                stroke_fill=(2, 6, 15, 190),
            )

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def add_landscape(image, level):
    """Finish the scene with hills, a distant city, and warm window lights."""
    random = np.random.default_rng(92)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Layered hills keep the bottom edge from feeling like a graph.
    distant_hill = [
        (0, 590),
        (130, 540),
        (260, 578),
        (420, 520),
        (590, 575),
        (760, 532),
        (930, 580),
        (1080, 525),
        (WIDTH, 560),
        (WIDTH, HEIGHT),
        (0, HEIGHT),
    ]
    draw.polygon(distant_hill, fill=(8, 14, 24, 238))

    near_hill = [
        (0, 640),
        (180, 595),
        (340, 628),
        (510, 580),
        (700, 640),
        (870, 594),
        (1030, 625),
        (WIDTH, 590),
        (WIDTH, HEIGHT),
        (0, HEIGHT),
    ]
    draw.polygon(near_hill, fill=(3, 7, 13, 255))

    pollution = (level - 1) / 8
    building_count = int(5 + pollution * 35)
    for _ in range(building_count):
        x = int(random.uniform(0, WIDTH))
        building_width = int(random.uniform(10, 28))
        building_height = int(random.uniform(12, 68) * (0.5 + pollution))
        base_y = int(623 + random.uniform(-8, 20))
        top_y = base_y - building_height
        draw.rectangle(
            (x, top_y, x + building_width, base_y),
            fill=(4, 7, 13, 255),
        )

        if level >= 4 and random.random() < 0.72:
            for window_y in range(top_y + 8, base_y - 4, 10):
                if random.random() < 0.56:
                    draw.rectangle(
                        (x + 4, window_y, x + 7, window_y + 3),
                        fill=(255, 185, 88, int(120 + pollution * 120)),
                    )

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def render_sky(level, show_lines=True, show_labels=False):
    """Render one complete SkyGlow scene and return it with the key metrics."""
    image = make_sky_background(level)
    image = add_milky_way(image, level)
    image, star_count = add_stars(image, level)
    image = add_named_stars(image, level, show_lines, show_labels)
    image = add_landscape(image, level)

    named_visible = sum(
        magnitude <= LIMITING_MAGNITUDES[level]
        for _, _, _, magnitude, _ in NAMED_STARS
    )

    metrics = {
        "visible_stars": star_count + named_visible,
        "limiting_magnitude": LIMITING_MAGNITUDES[level],
        "milky_way": MILKY_WAY_LABELS[level],
        "class_name": BORTLE_NAMES[level],
    }
    return image, metrics
