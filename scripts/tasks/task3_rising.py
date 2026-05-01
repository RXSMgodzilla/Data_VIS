import json
from collections import Counter, defaultdict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.common import (
    ARTIST_TYPES,
    OCEANUS,
    node_name,
    artist_primary_genre,
    works_for_artist,
    prepare_indexes,
    influence_records,
    find_sailor_id,
    OUTPUT_DIR,
    ensure_output_dir,
)


def build_rising_star_task(
    sailor_id,
    nodes,
    artist_to_works,
    collaborations_by_work,
    influence_in,
    influence_out,
):
    candidates = []
    active_after_year = 2035

    for artist_id, works in artist_to_works.items():
        node = nodes[artist_id]
        if node["Node Type"] not in ARTIST_TYPES:
            continue

        work_payload = works_for_artist(artist_id, artist_to_works, nodes)
        if not work_payload:
            continue

        release_years = [item["releaseYear"] for item in work_payload if item["releaseYear"] is not None]
        if not release_years or max(release_years) < active_after_year:
            continue

        genre_counts = Counter(item["genre"] for item in work_payload if item["genre"])
        oceanus_count = genre_counts[OCEANUS]
        if oceanus_count == 0:
            continue

        notable_count = sum(1 for item in work_payload if item["notable"])
        collaboration_degree = 0
        collaborators = set()
        for work_id in artist_to_works.get(artist_id, []):
            collaborators |= collaborations_by_work.get(work_id, set())
        collaborators.discard(artist_id)
        collaboration_degree = len(collaborators)

        influence_received = len(influence_out.get(artist_id, []))
        influence_absorbed = len(influence_in.get(artist_id, []))
        recency = max(release_years) - min(release_years) + 1
        oceanus_ratio = oceanus_count / max(len(work_payload), 1)

        score = (
            oceanus_ratio * 35
            + min(collaboration_degree, 12) * 2.5
            + min(notable_count, 6) * 4
            + min(influence_received, 8) * 3
            + min(influence_absorbed, 10) * 1.4
            + min(max(release_years) - active_after_year, 5) * 1.5
        )

        candidates.append(
            {
                "id": artist_id,
                "name": node_name(node),
                "nodeType": node["Node Type"],
                "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
                "latestYear": max(release_years),
                "careerStart": min(release_years),
                "worksCount": len(work_payload),
                "oceanusCount": oceanus_count,
                "oceanusRatio": round(oceanus_ratio, 3),
                "notableCount": notable_count,
                "collaborationDegree": collaboration_degree,
                "influenceReceived": influence_received,
                "influenceAbsorbed": influence_absorbed,
                "score": round(score, 2),
                "works": work_payload,
            }
        )

    candidates.sort(key=lambda item: (item["score"], item["oceanusRatio"], item["latestYear"]), reverse=True)
    candidates = [item for item in candidates if item["id"] != sailor_id]
    top_three = candidates[:3]

    reference_pool = [item for item in candidates if item["id"] == sailor_id]
    if not reference_pool:
        sailor_works = works_for_artist(sailor_id, artist_to_works, nodes)
        sailor_years = [item["releaseYear"] for item in sailor_works if item["releaseYear"] is not None]
        reference_pool = [
            {
                "id": sailor_id,
                "name": node_name(nodes[sailor_id]),
                "nodeType": nodes[sailor_id]["Node Type"],
                "primaryGenre": artist_primary_genre(sailor_id, nodes, artist_to_works),
                "latestYear": max(sailor_years) if sailor_years else None,
                "careerStart": min(sailor_years) if sailor_years else None,
                "worksCount": len(sailor_works),
                "oceanusCount": sum(1 for item in sailor_works if item["genre"] == OCEANUS),
                "oceanusRatio": 1.0,
                "notableCount": sum(1 for item in sailor_works if item["notable"]),
                "collaborationDegree": 0,
                "influenceReceived": len(influence_out.get(sailor_id, [])),
                "influenceAbsorbed": len(influence_in.get(sailor_id, [])),
                "score": 100,
                "works": sailor_works,
            }
        ]

    comparators = [reference_pool[0]]
    for candidate in candidates:
        if len(comparators) < 3:
            comparators.append(candidate)

    trajectories = []
    for candidate in comparators:
        timeline = defaultdict(lambda: {"releases": 0, "notable": 0, "influenceReceived": 0})
        for work in candidate["works"]:
            year = work["releaseYear"]
            if year is None:
                continue
            timeline[year]["releases"] += 1
            timeline[year]["notable"] += int(work["notable"])
        for record in influence_out.get(candidate["id"], []):
            if record["sourceYear"] is not None:
                timeline[record["sourceYear"]]["influenceReceived"] += 1
        trajectories.append(
            {
                "id": str(candidate["id"]),
                "name": candidate["name"],
                "series": [{"year": year, **timeline[year]} for year in sorted(timeline)],
            }
        )

    graph_nodes = []
    graph_edges = []
    selected = {sailor_id}
    selected.update(item["id"] for item in top_three)
    for candidate in top_three:
        for record in influence_in.get(candidate["id"], [])[:8]:
            selected.add(record["artist"])
        for record in influence_out.get(candidate["id"], [])[:8]:
            selected.add(record["artist"])

    for artist_id in selected:
        graph_nodes.append(
            {
                "id": str(artist_id),
                "label": node_name(nodes[artist_id]),
                "nodeType": nodes[artist_id]["Node Type"],
                "tier": "anchor" if artist_id == sailor_id else "predicted" if artist_id in {item["id"] for item in top_three} else "community",
                "genre": artist_primary_genre(artist_id, nodes, artist_to_works),
                "size": 24 if artist_id == sailor_id else 18 if artist_id in {item["id"] for item in top_three} else 12,
            }
        )

    for artist_id in selected:
        for record in influence_out.get(artist_id, []):
            target_artist = record["artist"]
            if target_artist not in selected:
                continue
            graph_edges.append(
                {
                    "id": f"{artist_id}-{target_artist}-{record['type']}",
                    "source": str(artist_id),
                    "target": str(target_artist),
                    "type": record["type"],
                }
            )

    return {
        "definition": {
            "summary": "A rising Oceanus Folk star stays active past 2035, remains genre-focused, collaborates broadly, and starts receiving stylistic echoes from peers.",
            "criteria": [
                "Recent activity after 2035",
                "High Oceanus Folk concentration",
                "Dense collaboration network",
                "Growing influence received from peers",
                "Early chart visibility through notable works",
            ],
        },
        "comparators": [
            {
                **{key: value for key, value in candidate.items() if key not in {"works"}},
                "worksPreview": candidate["works"][:5],
            }
            for candidate in comparators
        ],
        "candidates": [
            {
                **{key: value for key, value in candidate.items() if key not in {"works"}},
                "worksPreview": candidate["works"][:5],
            }
            for candidate in candidates[:12]
        ],
        "topThree": [str(item["id"]) for item in top_three],
        "trajectories": trajectories,
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
    }


if __name__ == "__main__":
    nodes, links, (work_to_artists, _work_to_staff, artist_to_works, _member_of, collaborations_by_work) = prepare_indexes()
    influence_in, influence_out, _yearly_spread = influence_records(nodes, links, work_to_artists, artist_to_works)
    sailor_id = find_sailor_id(nodes)

    task = build_rising_star_task(
        sailor_id,
        nodes,
        artist_to_works,
        collaborations_by_work,
        influence_in,
        influence_out,
    )

    ensure_output_dir()
    output_path = OUTPUT_DIR / "task3.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print(f"Wrote {output_path}")
