# SkyGlow

SkyGlow is an interactive light-pollution simulator that shows how the same night sky changes from a Bortle 1 dark site to a Bortle 9 inner-city sky.

![SkyGlow comparison](assets/skyglow-preview.png)

## Why I built it

Light pollution is usually explained with maps, numbers, or photographs taken under completely different conditions. I wanted to make the loss more immediate: keep one landscape and one field of stars, then let someone watch the sky disappear.

I also wanted the project to be honest about what it is. SkyGlow is an educational simulation, not a planetarium or an observing forecast.

## What it does

- Moves through Bortle classes 1–9 with an interactive slider
- Includes presets for dark-sky, rural, suburban, and central-city conditions
- Compares a pristine reference sky with the selected pollution level
- Fades faint stars and the Milky Way as skyglow increases
- Adds a warmer, brighter horizon and distant city lights
- Shows an approximate limiting magnitude and star count for the rendered view
- Toggles constellation guides and bright-star labels
- Downloads the selected scene as a PNG

Every sky scene is generated in Python. The app does not rely on a set of nine finished background pictures.

## How the simulation works

SkyGlow begins with a repeatable catalogue of stars with different positions, brightnesses, and colors. Each Bortle class has an approximate naked-eye limiting magnitude, so progressively fainter stars are hidden as light pollution increases.

The Milky Way is built from a curved brightness band and a small field of smoothed random noise. Its contrast falls as the sky becomes brighter. A warm gradient and distant window lights create the horizon glow.

A few bright stars are arranged into simplified versions of Orion and the Summer Triangle so the constellation toggle has something recognizable to reveal. Their placement is illustrative rather than a literal chart for a date and location.

## What I learned

The first versions looked like stars on a graph. The biggest improvement did not come from adding more stars; it came from building the scene in layers: a dark gradient, an uneven Milky Way, different star colors, atmospheric glow, and a foreground silhouette.

I also had to separate a clear visual explanation from a scientific prediction. The Bortle scale is useful, but visibility in real life also depends on weather, altitude, Moon phase, eyesight, and nearby lights. The app states that limitation instead of hiding it.

## Run it locally

```bash
git clone https://github.com/Hussain1802/skyglow.git
cd skyglow
python -m venv .venv
```

On Windows:

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Built with

- Python
- Streamlit
- NumPy
- Pillow

## Limitations

- The rendered star field is illustrative, not tied to a real time or location
- Limiting magnitudes and Milky Way visibility are approximate
- The simulation does not model weather, Moon phase, altitude, or individual eyesight
- The visible-star count describes this generated view, not the entire celestial sphere

