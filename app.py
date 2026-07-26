from io import BytesIO

import streamlit as st

from sky_scene import BORTLE_NAMES, render_sky


st.set_page_config(
    page_title="SkyGlow",
    page_icon="✦",
    layout="wide",
)


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at 72% 0%, rgba(38, 61, 112, .20), transparent 34rem),
                linear-gradient(180deg, #050914 0%, #070b14 100%);
        }

        .block-container {
            max-width: 1480px;
            padding-top: 2.4rem;
            padding-bottom: 4rem;
        }

        .eyebrow {
            color: #e9b96e;
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .16em;
            margin-bottom: .65rem;
            text-transform: uppercase;
        }

        .hero-title {
            color: #f6f8ff;
            font-size: clamp(3rem, 6vw, 5.7rem);
            font-weight: 760;
            letter-spacing: -.065em;
            line-height: .92;
            margin: 0;
        }

        .hero-copy {
            color: #aab5c9;
            font-size: 1.08rem;
            line-height: 1.7;
            margin: 1.15rem 0 1.8rem;
            max-width: 780px;
        }

        [data-testid="stMetric"] {
            background: rgba(13, 21, 39, .78);
            border: 1px solid rgba(164, 183, 218, .14);
            border-radius: 16px;
            padding: 1rem 1.15rem;
        }

        [data-testid="stMetricLabel"] {
            color: #9eabc1;
        }

        [data-testid="stImage"] img {
            border: 1px solid rgba(174, 192, 225, .14);
            border-radius: 18px;
            box-shadow: 0 18px 60px rgba(0, 0, 0, .30);
        }

        .scene-label {
            color: #e9edf7;
            font-size: .92rem;
            font-weight: 650;
            letter-spacing: .03em;
            margin: .2rem 0 .65rem;
        }

        .honesty-note {
            background: rgba(13, 21, 39, .58);
            border-left: 3px solid #e9b96e;
            border-radius: 0 10px 10px 0;
            color: #9faabd;
            font-size: .9rem;
            line-height: 1.55;
            margin-top: 1.25rem;
            padding: .85rem 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def choose_level(level):
    st.session_state.bortle_level = level


if "bortle_level" not in st.session_state:
    st.session_state.bortle_level = 5


st.markdown('<div class="eyebrow">Interactive night-sky simulator</div>', unsafe_allow_html=True)
st.markdown('<h1 class="hero-title">What does a city<br>take from the sky?</h1>', unsafe_allow_html=True)
st.markdown(
    """
    <p class="hero-copy">
        Move one real night-sky photograph from a protected dark site into the
        middle of a city and watch its contrast disappear into skyglow.
    </p>
    """,
    unsafe_allow_html=True,
)


st.subheader("Choose a sky")
preset_columns = st.columns(4)

preset_columns[0].button(
    "Dark-sky reserve",
    on_click=choose_level,
    args=(1,),
    width="stretch",
)
preset_columns[1].button(
    "Rural outskirts",
    on_click=choose_level,
    args=(3,),
    width="stretch",
)
preset_columns[2].button(
    "Suburban sky",
    on_click=choose_level,
    args=(5,),
    width="stretch",
)
preset_columns[3].button(
    "Central city",
    on_click=choose_level,
    args=(9,),
    width="stretch",
)

control_column, option_column = st.columns([1.7, 1])

with control_column:
    level = st.slider(
        "Bortle class",
        min_value=1,
        max_value=9,
        key="bortle_level",
        help="Bortle 1 represents an excellent dark site; Bortle 9 represents an inner-city sky.",
    )
    st.caption(f"Class {level} · {BORTLE_NAMES[level]}")

with option_column:
    view_mode = st.radio(
        "View mode",
        options=["Side by side", "Selected sky only"],
        horizontal=True,
    )


dark_sky, dark_metrics = render_sky(1)
selected_sky, selected_metrics = render_sky(level)


st.divider()

if view_mode == "Side by side":
    left_scene, right_scene = st.columns(2)

    with left_scene:
        st.markdown(
            '<div class="scene-label">REAL PHOTOGRAPH · BORTLE 1 REFERENCE</div>',
            unsafe_allow_html=True,
        )
        st.image(dark_sky, width="stretch")

    with right_scene:
        st.markdown(
            f'<div class="scene-label">SIMULATED SKY GLOW · BORTLE {level}</div>',
            unsafe_allow_html=True,
        )
        st.image(selected_sky, width="stretch")
else:
    st.markdown(
        f'<div class="scene-label">SIMULATED SKY GLOW · BORTLE {level}</div>',
        unsafe_allow_html=True,
    )
    st.image(selected_sky, width="stretch")

st.caption(
    "Source photograph: ESO/P. Horálek, Cerro Paranal, Chile · "
    "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · "
    "[Original image](https://www.eso.org/public/images/potw2033a/)"
)


st.subheader("What remains visible")
metric_columns = st.columns(4)

metric_columns[0].metric(
    "Approx. stars overhead",
    f"{selected_metrics['visible_stars']:,}",
    delta=f"{selected_metrics['visible_stars'] - dark_metrics['visible_stars']:,} from dark sky",
    delta_color="normal",
)
metric_columns[1].metric(
    "Limiting magnitude",
    f"{selected_metrics['limiting_magnitude']:.1f}",
)
metric_columns[2].metric(
    "Milky Way",
    selected_metrics["milky_way"],
)
metric_columns[3].metric(
    "Bortle class",
    f"{level} of 9",
)


if level <= 2:
    explanation = (
        "Faint stars fill the background and the Milky Way has obvious structure. "
        "This is the kind of sky many people now have to travel to see."
    )
elif level <= 4:
    explanation = (
        "The Milky Way is still visible, but its finer texture is fading. "
        "Fainter stars disappear first, leaving the main constellation patterns."
    )
elif level <= 6:
    explanation = (
        "The sky background is brighter and lower-contrast. The Milky Way becomes "
        "difficult, while bright stars still hold familiar constellations together."
    )
else:
    explanation = (
        "Skyglow overwhelms faint light. Only the brightest stars remain obvious, "
        "and the Milky Way is lost even though it is still physically overhead."
    )

st.info(explanation)


png_file = BytesIO()
selected_sky.save(png_file, format="PNG")

download_column, note_column = st.columns([1, 2.6], vertical_alignment="center")

with download_column:
    st.download_button(
        "Download selected sky",
        data=png_file.getvalue(),
        file_name=f"skyglow-bortle-{level}.png",
        mime="image/png",
        width="stretch",
    )

with note_column:
    st.caption(
        "The downloaded image keeps the photographer credit attached."
    )


with st.expander("How the simulation works"):
    st.write(
        """
        SkyGlow starts with a real panoramic exposure made at ESO's Paranal
        Observatory. As the Bortle level rises, the app selectively lowers the
        contrast of compact stars and adds progressively stronger atmospheric glow.
        The photographed foreground is preserved rather than blurred.

        This is still a visual simulation rather than a calibrated prediction for a
        particular address. Weather, eyesight, altitude, Moon phase, camera exposure,
        and local lighting can all change what a real observer or camera records.
        """
    )

st.markdown(
    """
    <div class="honesty-note">
        <strong>Designed to explain, not to predict.</strong>
        The base scene is a genuine ESO photograph; only the light-pollution effect is
        simulated. The visibility thresholds are approximate, and the original photograph
        is a long exposure rather than a literal naked-eye view.
    </div>
    """,
    unsafe_allow_html=True,
)
