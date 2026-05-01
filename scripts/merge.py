import json
from pathlib import Path

from lib.common import (
    prepare_indexes,
    influence_records,
    find_sailor_id,
    OUTPUT_DIR,
    ensure_output_dir,
)
from tasks.task1_sailor import build_sailor_task
from tasks.task2_spread import build_spread_task
from tasks.task3_rising import build_rising_star_task


def main():
    nodes, links, (work_to_artists, work_to_staff, artist_to_works, _member_of, collaborations_by_work) = prepare_indexes()
    influence_in, influence_out, yearly_spread = influence_records(nodes, links, work_to_artists, artist_to_works)
    sailor_id = find_sailor_id(nodes)

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
            "sourceFile": str(OUTPUT_DIR.parent.parent / "MC1_release" / "MC1_graph.json"),
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

    ensure_output_dir()
    output_path = OUTPUT_DIR / "analysis_bundle.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(bundle, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
