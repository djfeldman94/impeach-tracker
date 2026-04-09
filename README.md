# Impeachment Tracker

Track where every member of Congress and governor stands on impeaching Donald Trump. Interactive maps, contact info, and sample call scripts to help citizens make their voices heard.

**Live site:** [impeach-tracker.pages.dev](https://impeach-tracker.pages.dev)

## Features

- Interactive election-night-style maps for House (435 districts), Senate, and Governors
- Hover tooltips and click-through to detail pages
- Zoom and pan on the House district map
- Stance classifications: co-sponsor, publicly supports, leaning support, silent, leaning oppose, publicly opposes
- Personalized call scripts with talking points for each stance
- Contact info including DC and district office phone numbers
- Filterable member lists by stance, party, and state
- Automated data pipeline with LLM-powered stance classification

## Tech Stack

- **Framework:** [Astro](https://astro.build) (static site generation)
- **Maps:** [Svelte](https://svelte.dev) islands + [D3.js](https://d3js.org) + TopoJSON
- **Data:** JSON files from [@unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators)
- **Stance classification:** Web search + Claude Sonnet
- **Hosting:** Cloudflare Pages
- **CI/CD:** GitHub Actions

## Development

```bash
npm install
npm run dev
```

## Data Pipeline

Member data and contact info are fetched from public sources. Stance classifications use web search + Claude Sonnet for analysis.

```bash
# Set up Python environment
python -m venv scripts/.venv
source scripts/.venv/bin/activate
pip install -r scripts/requirements.txt

# Refresh member data (preserves existing stances)
python scripts/fetch_members.py
python scripts/fetch_contacts.py
python scripts/fetch_governors.py

# Run LLM stance classification (requires ANTHROPIC_API_KEY in .env)
python scripts/scrape_stances_llm.py --all --delay 1.0

# Or classify a single state
python scripts/scrape_stances_llm.py --state CA --chamber house

# Manual stance overrides
python scripts/override_stance.py search "Josh Harder"
python scripts/override_stance.py set "Josh Harder" publicly-supports \
  --summary "Joined calls for removal" \
  --source-url "https://example.com/article"
python scripts/override_stance.py list

# Validate data
python scripts/validate_data.py
```

## Rebuild GeoJSON (rarely needed)

```bash
bash scripts/build_geo.sh
```

Requires `mapshaper` (installed as a dev dependency). Downloads Census 2024 cartographic boundary files and converts to simplified TopoJSON.

## Contributing

If you believe a stance classification is incorrect, please [open an issue](https://github.com/djfeldman94/impeach-tracker/issues/new) with a source link. Pull requests welcome.

## License

MIT
