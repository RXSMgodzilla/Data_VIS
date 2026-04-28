# VAST Music Visualization

Interactive dashboard for the VAST Challenge 2025 MC1 dataset.

Current stack:

- `Vue 3`
- `Vite`
- custom `SVG` relationship views
- lightweight dashboard cards, timelines, and ranked lists

## Project contents

- `scripts/preprocess_data.py`
  - reads `../MC1_release/MC1_graph.json`
  - generates `public/data/analysis_bundle.json`
- `src/App.vue`
  - three task views aligned with the official MC1 questions
- `src/components/OrbitalGraph.vue`
  - interactive orbital relationship graph for Task 1 and Task 3
- `src/components/BarList.vue`
  - ranked comparison bars
- `src/components/TimelineList.vue`
  - compact time-based summary tables
- `src/components/NetworkSummary.vue`
  - grouped diffusion summaries for Task 2

## Run locally

```bash
npm install
python scripts/preprocess_data.py
npm run dev
```

If you already have `public/data/analysis_bundle.json`, you can skip the preprocessing step.

## Build

```bash
npm run build
```

## Task coverage

1. `Sailor Shift career profile`
   - interactive ego-style orbital graph
   - timeline of works, notable output, and influence received
   - top influencers and collaborators
2. `Oceanus Folk influence spread`
   - yearly spread summary
   - top influenced genres and artists
   - before/after inspiration comparison around Sailor Shift's breakout
3. `Rising star prediction`
   - benchmark trajectory summary
   - weighted candidate scoreboard
   - interactive prediction graph for the top candidates

## Notes

- The repo includes a generated `public/data/analysis_bundle.json` so the front end can run immediately.
- The original official dataset remains in the separate `MC1_release` folder and is not duplicated here.
