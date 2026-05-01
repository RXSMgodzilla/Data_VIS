import json
from collections import Counter

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.common import (
    WORK_TYPES,
    ARTIST_TYPES,
    OCEANUS,
    node_name,
    node_year,
    artist_primary_genre,
    prepare_indexes,
    influence_records,
    OUTPUT_DIR,
    ensure_output_dir,
)


def build_spread_task(
    sailor_breakout_year,
    nodes,
    artist_to_works,
    work_to_artists,
    influence_in,
    influence_out,
    yearly_spread,
):
    oceanus_work_ids = {
        node_id
        for node_id, node in nodes.items()
        if node["Node Type"] in WORK_TYPES and node.get("genre") == OCEANUS
    }
    oceanus_artist_ids = {
        artist_id
        for artist_id in artist_to_works
        if artist_primary_genre(artist_id, nodes, artist_to_works) == OCEANUS
    }

    genre_counter = Counter()
    artist_counter = Counter()
    diffusion_edges = Counter()
    inspiration_pre = Counter()
    inspiration_post = Counter()

    for artist_id in oceanus_artist_ids:
        for record in influence_out.get(artist_id, []):
            influenced_artist_id = record["artist"]
            artist_counter[influenced_artist_id] += 1
            if record["sourceGenre"]:
                genre_counter[record["sourceGenre"]] += 1
            diffusion_edges[(artist_id, influenced_artist_id)] += 1

    for work_id in oceanus_work_ids:
        work = nodes[work_id]
        work_year = node_year(work)
        target_bucket = inspiration_pre
        if sailor_breakout_year is not None and work_year is not None and work_year >= sailor_breakout_year:
            target_bucket = inspiration_post

        for artist_id in work_to_artists.get(work_id, []):
            for record in influence_in.get(artist_id, []):
                if record["source"] != work_id:
                    continue
                genre = None
                if record["targetType"] in WORK_TYPES:
                    genre = nodes[record["target"]].get("genre")
                elif record["targetType"] in ARTIST_TYPES:
                    genre = artist_primary_genre(record["target"], nodes, artist_to_works)
                if genre and genre != OCEANUS:
                    target_bucket[genre] += 1

    yearly = []
    for year in sorted(yearly_spread):
        payload = yearly_spread[year]
        yearly.append(
            {
                "year": year,
                "influencedWorks": payload["works"],
                "oceanusCreated": payload["oceanusCreated"],
                "directSamples": payload["DirectlySamples"],
                "covers": payload["CoverOf"],
                "styleBorrowing": payload["InStyleOf"],
                "lyricalReferences": payload["LyricalReferenceTo"],
                "interpolations": payload["InterpolatesFrom"],
            }
        )

    graph_nodes = []
    graph_edges = []
    top_oceanus = [
        artist_id for artist_id, _ in Counter(
            {
                artist_id: sum(weight for (source, _), weight in diffusion_edges.items() if source == artist_id)
                for artist_id in oceanus_artist_ids
            }
        ).most_common(6)
    ]
    top_influenced = [artist_id for artist_id, _ in artist_counter.most_common(10)]
    selected = set(top_oceanus + top_influenced)

    for artist_id in selected:
        graph_nodes.append(
            {
                "id": str(artist_id),
                "label": node_name(nodes[artist_id]),
                "nodeType": nodes[artist_id]["Node Type"],
                "tier": "oceanus" if artist_id in oceanus_artist_ids else "external",
                "genre": artist_primary_genre(artist_id, nodes, artist_to_works),
                "size": 22 if artist_id in top_oceanus else 15,
            }
        )
    for (source_id, target_id), weight in diffusion_edges.items():
        if source_id not in selected or target_id not in selected:
            continue
        graph_edges.append(
            {
                "id": f"{source_id}-{target_id}",
                "source": str(source_id),
                "target": str(target_id),
                "type": "OceanusInfluence",
                "weight": weight,
            }
        )

    return {
        "yearlySpread": yearly,
        "topGenres": [{"genre": genre, "count": count} for genre, count in genre_counter.most_common(12)],
        "topArtists": [
            {
                "id": str(artist_id),
                "name": node_name(nodes[artist_id]),
                "count": count,
                "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
            }
            for artist_id, count in artist_counter.most_common(12)
        ],
        "inspirationShift": {
            "breakoutYear": sailor_breakout_year,
            "before": [{"genre": genre, "count": count} for genre, count in inspiration_pre.most_common(10)],
            "after": [{"genre": genre, "count": count} for genre, count in inspiration_post.most_common(10)],
        },
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
    }


if __name__ == "__main__":
    nodes, links, (work_to_artists, _work_to_staff, artist_to_works, _member_of, _collaborations_by_work) = prepare_indexes()
    influence_in, influence_out, yearly_spread = influence_records(nodes, links, work_to_artists, artist_to_works)

    # Need sailor breakout year from Task 1 data or recompute a minimal version
    # For standalone run we read the existing task1.json if available,
    # otherwise default to None.
    sailor_breakout_year = None
    task1_path = OUTPUT_DIR / "task1.json"
    if task1_path.exists():
        with task1_path.open("r", encoding="utf-8") as f:
            task1 = json.load(f)
        sailor_breakout_year = task1.get("breakoutYear")

    task = build_spread_task(
        sailor_breakout_year,
        nodes,
        artist_to_works,
        work_to_artists,
        influence_in,
        influence_out,
        yearly_spread,
    )

    ensure_output_dir()
    output_path = OUTPUT_DIR / "task2.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print(f"Wrote {output_path}")
