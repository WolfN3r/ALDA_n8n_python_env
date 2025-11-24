#!/usr/bin/env python3
"""
Initial Sequence Pair + Placement Generator
Uses n8n_json_handler to communicate with n8n
"""

import json
from n8n_json_handler import create_n8n_processor


def generate_sequence_pair(block_names):
    """
    Basic deterministic initial SP:
      r+  = sorted by area descending
      r-  = reversed r+
    This yields feasible topological encoding:
    for any A before B in both → A is left of B
    for reversed in second → A placed below B
    (Murata et al., DAC'96; Balasa et al. DAC'99)
    """
    r_plus = list(block_names)
    r_minus = list(reversed(block_names))
    return r_plus, r_minus


def compute_initial_positions(blocks, r_plus, r_minus):
    """
    Simple O(n²) longest-path-like placement
    consistent with sequence-pair constraints:

      if pos(r+) < pos(r+) AND pos(r-) < pos(r-) → A left of B
      if pos(r+) < pos(r+) AND pos(r-) > pos(r-) → A below B

    Placement rule:
      scan in order of r+
      each new module tries to go at x=0
      lift y until no overlap with previous blocks that dominate it
    """
    pos_rp = {b: i for i, b in enumerate(r_plus)}
    pos_rm = {b: i for i, b in enumerate(r_minus)}

    placement = {}

    for b in r_plus:
        w = blocks[b]["width"]
        h = blocks[b]["height"]
        x = 0
        y = 0

        for a, p in placement.items():
            # If a must be left of b:
            if pos_rp[a] < pos_rp[b] and pos_rm[a] < pos_rm[b]:
                x = max(x, p["x"] + p["width"])
            # If a must be below b:
            if pos_rp[a] < pos_rp[b] and pos_rm[a] > pos_rm[b]:
                y = max(y, p["y"] + p["height"])

        placement[b] = {
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h)
        }

    return placement


def extract_default_blocks(block_json):
    """
    Same logic as 02_createBStarTree.py:
    Pick default variant for each block.
    Returns {name:{width,height}} dict.
    """
    result = {}
    for block in block_json:
        name = block.get("name")
        if not name:
            continue
        variant = None
        for v in block.get("variants", []):
            if v.get("is_default", False):
                variant = v
                break
        if variant:
            result[name] = {
                "width": float(variant["width"]),
                "height": float(variant["height"])
            }
    return result


def process_sequence_pair(json_data):
    """
    n8n entry point.
    1. parse blocks
    2. generate SP and placement
    3. attach to json_data['sequence_pair']
    """
    if "blocks" not in json_data:
        return {"error": "No blocks found in JSON"}

    # collect blocks
    blocks = extract_default_blocks(json_data["blocks"])
    if not blocks:
        return {"error": "No default variants in blocks"}

    names = list(blocks.keys())

    # Sequence Pair
    r_plus, r_minus = generate_sequence_pair(names)

    # placement
    placement = compute_initial_positions(blocks, r_plus, r_minus)

    # Convert placement → full geometry format
    full_placement = {
        name: {
            "x_min": p["x"],
            "y_min": p["y"],
            "x_max": p["x"] + p["width"],
            "y_max": p["y"] + p["height"],
            "width": p["width"],
            "height": p["height"]
        }
        for name, p in placement.items()
    }
    # append to json
    result = json_data.copy()
    result["sequence_pair"] = {
        "r_plus": r_plus,
        "r_minus": r_minus,
        "placement": full_placement
    }

    return result


if __name__ == "__main__":
    processor = create_n8n_processor(process_sequence_pair)
    processor()
