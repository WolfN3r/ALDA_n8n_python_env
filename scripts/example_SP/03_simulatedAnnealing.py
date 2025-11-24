#!/usr/bin/env python3
"""
Sequence-Pair Simulated Annealing Optimizer
- Reads JSON from n8n (via n8n_json_handler)
- Optimizes sequence pair + block variants
- Returns best placement + telemetry
"""

import math
import random
from n8n_json_handler import create_n8n_processor

# SA SETTINGS
INITIAL_TEMP = 1000.0
FINAL_TEMP = 0.5
COOLING_RATE = 0.90
MAX_ITERATIONS = 1000

AREA_WEIGHT = 10.0
DEAD_SPACE_WEIGHT = 100.0
ASPECT_WEIGHT = 10.0
TARGET_ASPECT_RATIO = 1.0


def extract_variants(json_data):
    """Get variants per block: {name: [ {width,height}, ... ]}"""
    variants = {}
    for block in json_data.get("blocks", []):
        name = block.get("name")
        if not name:
            continue
        vs = []
        for v in block.get("variants", []):
            try:
                vs.append({
                    "width": float(v["width"]),
                    "height": float(v["height"])
                })
            except Exception:
                continue
        if vs:
            variants[name] = vs
    return variants


def initial_sequence_pair(block_names, json_data):
    """Use existing SP if present, otherwise simple deterministic one."""
    sp = json_data.get("sequence_pair", {})
    r_plus = sp.get("r_plus")
    r_minus = sp.get("r_minus")
    if r_plus and r_minus and len(r_plus) == len(block_names):
        return list(r_plus), list(r_minus)

    names = sorted(block_names)
    return names, list(reversed(names))


def initial_variant_indices(variants, json_data):
    """Prefer default variants from blocks if present, else index 0."""
    default_idx = {name: 0 for name in variants}
    for block in json_data.get("blocks", []):
        name = block.get("name")
        if name not in variants:
            continue
        for i, v in enumerate(block.get("variants", [])):
            if v.get("is_default"):
                default_idx[name] = min(i, len(variants[name]) - 1)
                break
    return default_idx


def decode_sequence_pair(r_plus, r_minus, variants, var_idx):
    """Murata-style O(n^2) decoding into non-overlapping placement."""
    pos_p = {b: i for i, b in enumerate(r_plus)}
    pos_m = {b: i for i, b in enumerate(r_minus)}

    placement = {}
    for b in r_plus:
        w = variants[b][var_idx[b]]["width"]
        h = variants[b][var_idx[b]]["height"]
        x = 0.0
        y = 0.0
        for a, pa in placement.items():
            # a left of b
            if pos_p[a] < pos_p[b] and pos_m[a] < pos_m[b]:
                x = max(x, pa["x_min"] + pa["width"])
            # a below b
            if pos_p[a] < pos_p[b] and pos_m[a] > pos_m[b]:
                y = max(y, pa["y_min"] + pa["height"])

        placement[b] = {
            "x_min": x,
            "y_min": y,
            "width": w,
            "height": h,
            "x_max": x + w,
            "y_max": y + h
        }

    return placement


def evaluate_placement(placement):
    """Compute area, dead space, aspect ratio and fitness."""
    if not placement:
        return float("inf"), {}, {}

    used_area = 0.0
    max_x = 0.0
    max_y = 0.0

    for p in placement.values():
        used_area += p["width"] * p["height"]
        max_x = max(max_x, p["x_max"])
        max_y = max(max_y, p["y_max"])

    total_area = max_x * max_y if max_x > 0 and max_y > 0 else 0.0
    dead_space = max(total_area - used_area, 0.0)
    dead_space_ratio = (dead_space / total_area * 100.0) if total_area > 0 else 0.0
    aspect_ratio = (max_x / max_y) if max_y > 0 else 0.0

    fitness = (
        AREA_WEIGHT * total_area +
        DEAD_SPACE_WEIGHT * dead_space_ratio +
        ASPECT_WEIGHT * abs(aspect_ratio - TARGET_ASPECT_RATIO)
    )

    metrics = {
        "total_area": total_area,
        "used_area": used_area,
        "dead_space": dead_space,
        "dead_space_percentage": dead_space_ratio,
        "aspect_ratio": aspect_ratio,
        "placement_width": max_x,
        "placement_height": max_y
    }

    return fitness, metrics, {"max_x": max_x, "max_y": max_y}


def random_neighbor_state(r_plus, r_minus, var_idx, variants):
    """Generate neighbor by swapping in SP or changing variant."""
    # shallow copies
    new_rp = list(r_plus)
    new_rm = list(r_minus)
    new_var_idx = dict(var_idx)

    move_type = random.randint(0, 2)

    if move_type == 0 and len(new_rp) > 1:
        i, j = random.sample(range(len(new_rp)), 2)
        new_rp[i], new_rp[j] = new_rp[j], new_rp[i]
    elif move_type == 1 and len(new_rm) > 1:
        i, j = random.sample(range(len(new_rm)), 2)
        new_rm[i], new_rm[j] = new_rm[j], new_rm[i]
    else:
        # change variant of random block
        name = random.choice(list(variants.keys()))
        n_var = len(variants[name])
        if n_var > 1:
            old = new_var_idx.get(name, 0)
            choices = [k for k in range(n_var) if k != old]
            if choices:
                new_var_idx[name] = random.choice(choices)

    return new_rp, new_rm, new_var_idx


def sa_optimize(json_data):
    """Main optimization entry for n8n."""
    variants = extract_variants(json_data)
    if not variants:
        return {"error": "No block variants found", "success": False}

    block_names = list(variants.keys())
    r_plus, r_minus = initial_sequence_pair(block_names, json_data)
    var_idx = initial_variant_indices(variants, json_data)

    # initial solution
    placement = decode_sequence_pair(r_plus, r_minus, variants, var_idx)
    cur_fit, cur_metrics, cur_bounds = evaluate_placement(placement)

    best_rp = list(r_plus)
    best_rm = list(r_minus)
    best_var_idx = dict(var_idx)
    best_fit = cur_fit
    best_metrics = cur_metrics
    best_placement = placement

    T = INITIAL_TEMP
    iterations = 0

    while T > FINAL_TEMP and iterations < MAX_ITERATIONS:
        rpn, rmn, vin = random_neighbor_state(r_plus, r_minus, var_idx, variants)
        pl_n = decode_sequence_pair(rpn, rmn, variants, vin)
        fit_n, met_n, _ = evaluate_placement(pl_n)

        delta = fit_n - cur_fit
        accept = delta < 0 or random.random() < math.exp(-delta / T if T > 0 else -1e9)

        if accept:
            r_plus, r_minus, var_idx = rpn, rmn, vin
            cur_fit, cur_metrics = fit_n, met_n
            placement = pl_n

            if fit_n < best_fit:
                best_fit = fit_n
                best_metrics = met_n
                best_rp = list(rpn)
                best_rm = list(rmn)
                best_var_idx = dict(vin)
                best_placement = pl_n

        iterations += 1
        T *= COOLING_RATE

    # Build placement dict with required fields
    placement_out = {}
    for name, p in best_placement.items():
        placement_out[name] = {
            "x_min": round(p["x_min"], 2),
            "y_min": round(p["y_min"], 2),
            "x_max": round(p["x_max"], 2),
            "y_max": round(p["y_max"], 2),
            "width": round(p["width"], 2),
            "height": round(p["height"], 2)
        }

    # Update JSON
    result = dict(json_data)  # shallow copy is enough

    result["sequence_pair"] = {
        "r_plus": best_rp,
        "r_minus": best_rm,
        "placement": placement_out
    }

    max_x = best_metrics["placement_width"]
    max_y = best_metrics["placement_height"]

    result["optimization_results"] = {
        "fitness_function": round(best_fit, 2),
        "total_area": round(best_metrics["total_area"], 2),
        "used_area": round(best_metrics["used_area"], 2),
        "dead_space": round(best_metrics["dead_space"], 2),
        "dead_space_percentage": round(best_metrics["dead_space_percentage"], 2),
        "aspect_ratio": round(best_metrics["aspect_ratio"], 2),
        "placement_width": round(max_x, 2),
        "placement_height": round(max_y, 2),
        "actual_iterations": iterations,
        "optimization_method": "simulated_annealing_sequence_pair"
    }

    # n8n_json_handler already ensures UTF-8-safe I/O
    return result


if __name__ == "__main__":
    processor = create_n8n_processor(sa_optimize)
    processor()
