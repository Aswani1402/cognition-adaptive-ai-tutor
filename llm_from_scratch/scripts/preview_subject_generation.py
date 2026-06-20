import argparse
import json

from src.cognitutor_lm_config import BY_SUBJECT_DIR, PACKET_OUTPUT, ROOT
from src.concept_resource_loader import safe_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()
    subject_path = BY_SUBJECT_DIR / f"{safe_name(args.domain)}.json"
    rows = json.loads(subject_path.read_text(encoding="utf-8")) if subject_path.exists() else []
    packets = json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []
    by_concept = {}
    for row in rows:
        by_concept.setdefault((row["concept_id"], row["concept_name"]), []).append(row)
    packet_counts = {}
    for packet in packets:
        if packet["domain"].lower() == args.domain.lower():
            packet_counts[packet["concept_id"]] = packet_counts.get(packet["concept_id"], 0) + 1

    header = "concept_id | concept_name | task_count | packet_count | avg_quality | status"
    print(header)
    lines = ["# Subject Generation Preview", "", header, "--- | --- | ---: | ---: | ---: | ---"]
    for (cid, name), items in sorted(by_concept.items()):
        avg = round(sum(float(i.get("quality_score", 0)) for i in items) / len(items), 3) if items else 0.0
        status = "PASS" if len(items) == 89 and avg >= 0.95 else "FAIL"
        line = f"{cid} | {name} | {len(items)} | {packet_counts.get(cid, 0)} | {avg} | {status}"
        print(line)
        lines.append(line)
    preview_dir = ROOT / "outputs" / "model_generated" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    path = preview_dir / f"subject_{safe_name(args.domain)}_generation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"preview_saved: {path}")


if __name__ == "__main__":
    main()
