import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "MC1_release" / "MC1_graph.json"
OUTPUT = ROOT / "vast-music-visualization" / "public" / "data" / "analysis_bundle.json"

INFLUENCE_EDGE_TYPES = {
    "InStyleOf",
    "InterpolatesFrom",
    "CoverOf",
    "LyricalReferenceTo",
    "DirectlySamples",
}
CREATIVE_EDGE_TYPES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}
WORK_TYPES = {"Song", "Album"}
ARTIST_TYPES = {"Person", "MusicalGroup"}
OCEANUS = "Oceanus Folk"


def parse_year(value):
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def load_graph():
    with SOURCE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    nodes = {node["id"]: node for node in data["nodes"]}
    links = data["links"]
    return nodes, links


def build_indexes(nodes, links):
    work_to_artists = defaultdict(set)
    work_to_staff = defaultdict(lambda: defaultdict(set))
    artist_to_works = defaultdict(set)
    member_of = defaultdict(set)
    collaborations_by_work = defaultdict(set)

    for edge in links:
        source = edge["source"]
        target = edge["target"]
        edge_type = edge["Edge Type"]
        source_node = nodes[source]
        target_node = nodes[target]

        if edge_type == "PerformerOf" and target_node["Node Type"] in WORK_TYPES:
            work_to_artists[target].add(source)
            artist_to_works[source].add(target)
            collaborations_by_work[target].add(source)

        if edge_type in CREATIVE_EDGE_TYPES and target_node["Node Type"] in WORK_TYPES:
            if source_node["Node Type"] in ARTIST_TYPES:
                work_to_staff[target][edge_type].add(source)
                collaborations_by_work[target].add(source)
                if edge_type == "PerformerOf":
                    artist_to_works[source].add(target)

        if edge_type == "MemberOf":
            member_of[source].add(target)

    return work_to_artists, work_to_staff, artist_to_works, member_of, collaborations_by_work


def node_name(node):
    return node.get("stage_name") or node.get("name") or f"Node {node['id']}"


def node_year(node):
    for key in ("release_date", "written_date", "notoriety_date"):
        year = parse_year(node.get(key))
        if year is not None:
            return year
    return None


def artist_primary_genre(artist_id, nodes, artist_to_works):
    genres = Counter()
    for work_id in artist_to_works.get(artist_id, []):
        genre = nodes[work_id].get("genre")
        if genre:
            genres[genre] += 1
    return genres.most_common(1)[0][0] if genres else "Mixed"


def works_for_artist(artist_id, artist_to_works, nodes):
    works = []
    for work_id in artist_to_works.get(artist_id, []):
        node = nodes[work_id]
        works.append(
            {
                "id": work_id,
                "name": node_name(node),
                "type": node["Node Type"],
                "genre": node.get("genre"),
                "releaseYear": parse_year(node.get("release_date")),
                "notable": bool(node.get("notable")),
            }
        )
    works.sort(key=lambda item: (item["releaseYear"] or 0, item["name"]))
    return works


def influence_records(nodes, links, work_to_artists, artist_to_works):
    artist_influence_in = defaultdict(list)
    artist_influence_out = defaultdict(list)
    yearly_spread = defaultdict(Counter)

    for edge in links:
        edge_type = edge["Edge Type"]
        if edge_type not in INFLUENCE_EDGE_TYPES:
            continue

        source_id = edge["source"]
        target_id = edge["target"]
        source_node = nodes[source_id]
        target_node = nodes[target_id]

        source_year = node_year(source_node)
        source_artists = set()
        if source_node["Node Type"] in WORK_TYPES:
            source_artists |= work_to_artists.get(source_id, set())
        elif source_node["Node Type"] in ARTIST_TYPES:
            source_artists.add(source_id)

        target_artists = set()
        if target_node["Node Type"] in WORK_TYPES:
            target_artists |= work_to_artists.get(target_id, set())
        elif target_node["Node Type"] in ARTIST_TYPES:
            target_artists.add(target_id)

        target_genre = target_node.get("genre")
        source_genre = source_node.get("genre")

        record = {
            "type": edge_type,
            "source": source_id,
            "target": target_id,
            "sourceYear": source_year,
            "sourceGenre": source_genre,
            "targetGenre": target_genre,
            "sourceType": source_node["Node Type"],
            "targetType": target_node["Node Type"],
        }

        for source_artist in source_artists:
            for target_artist in target_artists:
                if source_artist == target_artist:
                    continue
                artist_influence_in[source_artist].append(
                    {**record, "artist": target_artist}
                )
                artist_influence_out[target_artist].append(
                    {**record, "artist": source_artist}
                )

        source_is_oceanus = source_genre == OCEANUS
        target_is_oceanus = (
            target_genre == OCEANUS
            or any(artist_primary_genre(artist, nodes, artist_to_works) == OCEANUS for artist in target_artists)
        )
        if target_is_oceanus and source_year is not None:
            yearly_spread[source_year]["works"] += 1
            yearly_spread[source_year][edge_type] += 1
            for artist in source_artists:
                yearly_spread[source_year][f"artist::{artist}"] += 1
            if source_genre:
                yearly_spread[source_year][f"genre::{source_genre}"] += 1
        if source_is_oceanus and source_year is not None:
            yearly_spread[source_year]["oceanusCreated"] += 1

    return artist_influence_in, artist_influence_out, yearly_spread


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
                }
            )
            if performer_id != sailor_id:
                collaborator_counter[performer_id] += 1
                collaborator_roles[performer_id].add("PerformerOf")
                collaborator_work_map[performer_id].add(work_id)

    influencer_counter = Counter()
    influencer_types = defaultdict(Counter)
    influenced_counter = Counter()
    influenced_types = defaultdict(Counter)

    for record in influence_in.get(sailor_id, []):
        influencer_id = record["artist"]
        influencer_counter[influencer_id] += 1
        influencer_types[influencer_id][record["type"]] += 1
        if record["targetType"] in WORK_TYPES:
            graph_nodes.add(record["target"])
        graph_nodes.add(influencer_id)
        graph_edges.append(
            {
                "id": f"in-{record['source']}-{record['target']}-{record['type']}",
                "source": record["source"],
                "target": record["target"],
                "type": record["type"],
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
        for collaborator_id, _ in collaborator_counter.most_common(12)
    ]

    top_influencers = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "count": count,
            "types": dict(influencer_types[artist_id]),
            "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
        }
        for artist_id, count in influencer_counter.most_common(10)
    ]

    indirect_influence = Counter()
    direct_set = {artist_id for artist_id, _ in influenced_counter.items()}
    for direct_artist in direct_set:
        for downstream in influence_out.get(direct_artist, []):
            indirect_influence[downstream["artist"]] += 1

    influenced_artists = [
        {
            "id": str(artist_id),
            "name": node_name(nodes[artist_id]),
            "directCount": count,
            "indirectCount": indirect_influence[artist_id],
            "primaryGenre": artist_primary_genre(artist_id, nodes, artist_to_works),
            "types": dict(influenced_types[artist_id]),
        }
        for artist_id, count in influenced_counter.most_common(12)
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
        "works": sailor_works,
    }


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


def main():
    nodes, links = load_graph()
    (
        work_to_artists,
        work_to_staff,
        artist_to_works,
        _member_of,
        collaborations_by_work,
    ) = build_indexes(nodes, links)
    influence_in, influence_out, yearly_spread = influence_records(
        nodes, links, work_to_artists, artist_to_works
    )

    sailor_id = next(
        node_id for node_id, node in nodes.items() if node_name(node) == "Sailor Shift"
    )

    sailor_task = build_sailor_task(
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
    spread_task = build_spread_task(
        sailor_task["breakoutYear"],
        nodes,
        artist_to_works,
        work_to_artists,
        influence_in,
        influence_out,
        yearly_spread,
    )
    rising_task = build_rising_star_task(
        sailor_id,
        nodes,
        artist_to_works,
        collaborations_by_work,
        influence_in,
        influence_out,
    )

    bundle = {
        "meta": {
            "sourceFile": str(SOURCE.relative_to(ROOT)),
            "nodeCount": len(nodes),
            "edgeCount": len(links),
            "generatedFor": "VAST Challenge 2025 MC1 interactive dashboard",
        },
        "tasks": {
            "sailor": sailor_task,
            "spread": spread_task,
            "rising": rising_task,
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(bundle, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
