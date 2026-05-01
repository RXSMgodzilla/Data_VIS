import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "MC1_graph.json"
OUTPUT_DIR = ROOT / "public" / "data"

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


def prepare_indexes():
    """Convenience wrapper: load graph and build all indexes."""
    nodes, links = load_graph()
    indexes = build_indexes(nodes, links)
    return nodes, links, indexes


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


def find_sailor_id(nodes):
    return next(
        node_id for node_id, node in nodes.items() if node_name(node) == "Sailor Shift"
    )


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
