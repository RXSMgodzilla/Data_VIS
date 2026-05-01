import json
from collections import Counter, defaultdict

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
    works_for_artist,
    prepare_indexes,
    influence_records,
    find_sailor_id,
    OUTPUT_DIR,
    ensure_output_dir,
)


def build_sailor_task(
    sailor_id,
    nodes,
    links,
    work_to_artists,
    work_to_staff,
    artist_to_works,
    collaborations_by_work,
    influence_in,
    influence_out,
):
    sailor_works = works_for_artist(sailor_id, artist_to_works, nodes)
    sailor_work_ids = {item["id"] for item in sailor_works}
    graph_nodes = {sailor_id}
    graph_edges = []
    collaborator_counter = Counter()
    collaborator_roles = defaultdict(set)
    collaborator_work_map = defaultdict(set)

    for work_id in sailor_work_ids:
        graph_nodes.add(work_id)
        work_node = nodes[work_id]
        for edge_type, people in work_to_staff.get(work_id, {}).items():
            for person_id in people:
                graph_nodes.add(person_id)
                graph_edges.append(
                    {
                        "id": f"{person_id}-{work_id}-{edge_type}",
                        "source": person_id,
                        "target": work_id,
                        "type": edge_type,
                        "year": parse_year(work_node.get("release_date")),
                    }
                )
                if person_id != sailor_id:
                    collaborator_counter[person_id] += 1
                    collaborator_roles[person_id].add(edge_type)
                    collaborator_work_map[person_id].add(work_id)

        for performer_id in work_to_artists.get(work_id, []):
            graph_nodes.add(performer_id)
            graph_edges.append(
                {
                    "id": f"{performer_id}-{work_id}-PerformerOf",
                    "source": performer_id,
                    "target": work_id,
                    "type": "PerformerOf",
                    "year": parse_year(work_node.get("release_date")),
                }
            )
            if performer_id != sailor_id:
                collaborator_counter[performer_id] += 1
                collaborator_roles[performer_id].add("PerformerOf")
                collaborator_work_map[performer_id].add(work_id)

    influencer_counter = Counter()
    influencer_types = defaultdict(Counter)
    influencer_yearly = defaultdict(Counter)
    influenced_counter = Counter()
    influenced_types = defaultdict(Counter)

    for record in influence_in.get(sailor_id, []):
        influencer_id = record["artist"]
        influencer_counter[influencer_id] += 1
        influencer_types[influencer_id][record["type"]] += 1
        if record.get("sourceYear") is not None:
            influencer_yearly[influencer_id][record["sourceYear"]] += 1
        if record["targetType"] in WORK_TYPES:
            graph_nodes.add(record["target"])
        graph_nodes.add(influencer_id)
        graph_edges.append(
            {
                "id": f"in-{record['source']}-{record['target']}-{record['type']}",
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
                "year": record.get("sourceYear"),
            }
        )

    for record in influence_out.get(sailor_id, []):
        influenced_id = record["artist"]
        influenced_counter[influenced_id] += 1
        influenced_types[influenced_id][record["type"]] += 1
        if record["sourceType"] in WORK_TYPES:
            graph_nodes.add(record["source"])
        graph_nodes.add(influenced_id)
        graph_edges.append(
            {
                "id": f"out-{record['source']}-{record['target']}-{record['type']}",
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
                "year": record.get("sourceYear"),
            }
        )

    timeline = defaultdict(lambda: {"works": 0, "notableWorks": 0, "influenceIn": 0, "influenceOut": 0})
    for work in sailor_works:
        year = work["releaseYear"]
        if year is None:
            continue
        timeline[year]["works"] += 1
        timeline[year]["notableWorks"] += int(work["notable"])
    for record in influence_in.get(sailor_id, []):
        if record["sourceYear"] is not None:
            timeline[record["sourceYear"]]["influenceIn"] += 1
    for record in influence_out.get(sailor_id, []):
        if record["sourceYear"] is not None:
            timeline[record["sourceYear"]]["influenceOut"] += 1

    node_payload = []
    for node_id in graph_nodes:
        node = nodes[node_id]
        primary_type = node["Node Type"]
        if node_id == sailor_id:
            tier = "core"
        elif node_id in sailor_work_ids:
            tier = "work"
        elif node_id in influencer_counter:
            tier = "influencer"
        elif node_id in influenced_counter:
            tier = "influenced"
        else:
            tier = "collaborator"

        node_payload.append(
            {
                "id": str(node_id),
                "label": node_name(node),
                "nodeType": primary_type,
                "tier": tier,
                "genre": node.get("genre"),
                "year": node_year(node),
                "size": 26 if tier == "core" else 16 if primary_type in ARTIST_TYPES else 10,
                "notable": bool(node.get("notable")),
            }
        )

    edge_payload = []
    seen_edges = set()
    for edge in graph_edges:
        key = (str(edge["source"]), str(edge["target"]), edge["type"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edge_payload.append(
            {
                "id": edge["id"],
                "source": str(edge["source"]),
                "target": str(edge["target"]),
                "type": edge["type"],
                "year": edge.get("year"),
            }
        )

    collaborators = [
        {
            "id": str(collaborator_id),
            "name": node_name(nodes[collaborator_id]),
            "roles": sorted(collaborator_roles[collaborator_id]),
            "collaborations": collaborator_counter[collaborator_id],
            "works": sorted(node_name(nodes[work_id]) for work_id in collaborator_work_map[collaborator_id])[:4],
            "primaryGenre": artist_primary_genre(collaborator_id, nodes, artist_to_works),
        }
        for collaborator_id, _ in collaborator_counter.most_common()
    ]

    collaborator_downstream = []
    for collaborator_id in collaborator_counter:
        downstream_map = defaultdict(lambda: {"count": 0, "years": []})
        for record in influence_out.get(collaborator_id, []):
            target = record["artist"]
            downstream_map[target]["count"] += 1
            if record.get("sourceYear") is not None:
                downstream_map[target]["years"].append(record["sourceYear"])
        if downstream_map:
            downstream_list = []
            for artist_id, data in sorted(downstream_map.items(), key=lambda x: -x[1]["count"]):
                item = {
                    "id": str(artist_id),
                    "name": node_name(nodes[artist_id]),
                    "count": data["count"],
                    "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
                }
                if data["years"]:
                    item["year"] = min(data["years"])
                downstream_list.append(item)
            collaborator_downstream.append({
                "collaboratorId": str(collaborator_id),
                "collaboratorName": node_name(nodes[collaborator_id]),
                "downstream": downstream_list,
            })

    top_influencers = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "count": count,
            "types": dict(influencer_types[artist_id]),
            "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
            "yearlyCount": dict(influencer_yearly[artist_id]),
        }
        for artist_id, count in influencer_counter.most_common()
    ]

    indirect_influence = Counter()
    indirect_via = defaultdict(set)
    direct_set = {artist_id for artist_id, _ in influenced_counter.items()}
    for direct_artist in direct_set:
        for downstream in influence_out.get(direct_artist, []):
            indirect_influence[downstream["artist"]] += 1
            indirect_via[downstream["artist"]].add(direct_artist)

    influenced_artists = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "directCount": count,
            "indirectCount": indirect_influence[artist_id],
            "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
            "types": dict(influenced_types[artist_id]),
        }
        for artist_id, count in influenced_counter.most_common()
    ]

    indirect_only_artists = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "indirectCount": count,
            "viaArtists": [
                {"id": str(via_id), "name": node_name(nodes[via_id])}
                for via_id in sorted(indirect_via[artist_id])
            ],
            "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
        }
        for artist_id, count in indirect_influence.most_common()
        if artist_id not in influenced_counter
    ]

    community_counter = Counter()
    community_years = defaultdict(list)
    for record in influence_out.get(sailor_id, []):
        target_id = record["artist"]
        genre = artist_primary_genre(target_id, nodes, artist_to_works)
        if genre == OCEANUS:
            community_counter[target_id] += 1
            if record.get("sourceYear") is not None:
                community_years[target_id].append(record["sourceYear"])

    community_influence = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "count": count,
            "isOceanus": True,
            "primaryGenre": OCEANUS,
            "year": min(community_years[artist_id]) if community_years.get(artist_id) else None,
        }
        for artist_id, count in community_counter.most_common()
    ]

    years = sorted(timeline)
    year_range = [years[0], years[-1]] if years else [1990, 2040]
    breakout_year = None
    notable_years = [parse_year(nodes[work["id"]].get("notoriety_date")) for work in sailor_works if nodes[work["id"]].get("notoriety_date")]
    notable_years = [year for year in notable_years if year is not None]
    if notable_years:
        breakout_year = min(notable_years)
    elif sailor_works and sailor_works[0]["releaseYear"] is not None:
        breakout_year = sailor_works[0]["releaseYear"]

    return {
        "artistId": str(sailor_id),
        "artistName": node_name(nodes[sailor_id]),
        "breakoutYear": breakout_year,
        "yearRange": year_range,
        "graph": {"nodes": node_payload, "edges": edge_payload},
        "timeline": [{"year": year, **timeline[year]} for year in years],
        "topInfluencers": top_influencers,
        "collaborators": collaborators,
        "influencedArtists": influenced_artists,
        "indirectOnlyArtists": indirect_only_artists,
        "collaboratorDownstream": collaborator_downstream,
        "communityInfluence": community_influence,
        "works": sailor_works,
    }


def parse_year(value):
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


if __name__ == "__main__":
    nodes, links, (work_to_artists, work_to_staff, artist_to_works, _member_of, collaborations_by_work) = prepare_indexes()
    influence_in, influence_out, _yearly_spread = influence_records(nodes, links, work_to_artists, artist_to_works)
    sailor_id = find_sailor_id(nodes)

    task = build_sailor_task(
        sailor_id,
        nodes,
        links,
        work_to_artists,
        work_to_staff,
        artist_to_works,
        collaborations_by_work,
        influence_in,
        influence_out,
    )

    ensure_output_dir()
    output_path = OUTPUT_DIR / "task1.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print(f"Wrote {output_path}")
