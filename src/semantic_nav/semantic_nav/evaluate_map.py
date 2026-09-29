"""Compare the semantic map snapshot with ground truth.

  ros2 run semantic_nav evaluate_map --pred /tmp/semantic_map.json \
      --gt src/semantic_nav/eval/ground_truth_example.yaml --max-dist 1.0
"""
import argparse
import json

import yaml

from semantic_nav.evaluation import match_objects


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pred", required=True, help="JSON snapshot written by semantic_map")
    ap.add_argument("--gt", required=True, help="YAML ground truth")
    ap.add_argument("--max-dist", type=float, default=1.0)
    args = ap.parse_args()

    pred = json.load(open(args.pred))
    gt = yaml.safe_load(open(args.gt))["objects"]
    r = match_objects(pred, gt, args.max_dist)
    print(f"objects: {len(pred)} predicted / {len(gt)} ground truth / {r['matched']} matched")
    print(f"precision {r['precision']:.2f}   recall {r['recall']:.2f}")
    print(f"localisation error: mean {r['mean_error_m']:.3f} m, median {r['median_error_m']:.3f} m")
    for label, s in r["per_label"].items():
        print(f"  {label:<15} pred {s['pred']}  gt {s['gt']}  matched {s['matched']}")


if __name__ == "__main__":
    main()
