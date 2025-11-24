#!/usr/bin/env python3
"""
Sequence-Pair Layout Visualizer for n8n

Left:  block placement from sequence_pair.placement
Right: top = horizontal constraint graph G_H
       bottom = vertical constraint graph G_V
"""

import sys
import colorsys
import matplotlib

# Xming-compatible backend
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

from n8n_json_handler import create_n8n_processor

def short_label(name: str):
    if "BLOCK_" in name:
        return name.replace("BLOCK_", "")
    return name

def generate_colors(names):
    """Simple distinct colors for blocks."""
    n = len(names)
    colors = {}
    for i, name in enumerate(names):
        hue = (i * 0.61803398875) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.9)
        colors[name] = (r, g, b)
    return colors


def build_constraint_graphs(r_plus, r_minus):
    """
    Build horizontal (left-of) and vertical (below) constraint graphs
    from sequence pair, following Murata/Lai.
    """
    pos_p = {b: i for i, b in enumerate(r_plus)}
    pos_m = {b: i for i, b in enumerate(r_minus)}
    names = list(r_plus)

    edges_h = []  # a -> b, a left of b
    edges_v = []  # a -> b, a below b

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            pa, pb = pos_p[a], pos_p[b]
            ma, mb = pos_m[a], pos_m[b]

            if pa < pb:
                if ma < mb:
                    edges_h.append((a, b))
                else:
                    edges_v.append((a, b))
            else:
                if mb < ma:
                    edges_h.append((b, a))
                else:
                    edges_v.append((b, a))

    return edges_h, edges_v, pos_p, pos_m


def visualize_sequence_pair(json_data):
    """Main n8n processing + visualization function."""
    data = json_data[0] if isinstance(json_data, list) else json_data

    if "sequence_pair" not in data:
        return {"success": False, "error": "Missing 'sequence_pair' in JSON"}

    sp = data["sequence_pair"]
    placement = sp.get("placement", {})
    r_plus = sp.get("r_plus", [])
    r_minus = sp.get("r_minus", [])

    if not placement or not r_plus or not r_minus:
        return {"success": False, "error": "Incomplete sequence_pair data"}

    names = list(placement.keys())
    colors = generate_colors(names)

    # ---------- Build constraint graphs ----------
    edges_h, edges_v, pos_p, pos_m = build_constraint_graphs(r_plus, r_minus)
    n = len(names)

    # Node positions on n×n grid (intersection of r+ and r- indices)
    node_pos = {
        name: (pos_p[name] + 1, pos_m[name] + 1) for name in names
    }

    # ---------- Figure / axes layout ----------
    fig = plt.figure(figsize=(12, 6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 1])

    ax_place = fig.add_subplot(gs[:, 0])
    ax_h = fig.add_subplot(gs[0, 1])
    ax_v = fig.add_subplot(gs[1, 1])

    fig.suptitle("Sequence-Pair Placement & Constraint Graphs")

    # ---------- Left: placement ----------
    xs = [p["x_min"] for p in placement.values()]
    ys = [p["y_min"] for p in placement.values()]
    x2 = [p["x_max"] for p in placement.values()]
    y2 = [p["y_max"] for p in placement.values()]

    xmin, xmax = min(xs), max(x2)
    ymin, ymax = min(ys), max(y2)
    w = xmax - xmin
    h = ymax - ymin
    margin = 0.05 * max(w, h)

    ax_place.set_title("Block Placement")
    ax_place.set_aspect("equal")
    ax_place.set_xlim(xmin - margin, xmax + margin)
    ax_place.set_ylim(ymin - margin, ymax + margin)
    ax_place.set_xlabel("X")
    ax_place.set_ylabel("Y")

    for name, p in placement.items():
        x0, y0 = p["x_min"], p["y_min"]
        width, height = p["width"], p["height"]
        rect = Rectangle(
            (x0, y0),
            width,
            height,
            facecolor=colors.get(name, (0.8, 0.8, 0.8)),
            edgecolor="black",
            alpha=0.8,
        )
        ax_place.add_patch(rect)
        ax_place.text(
            x0 + width / 2,
            y0 + height / 2,
            name,
            ha="center",
            va="center",
            fontsize=9,
        )

    # ---------- Helper: draw one grid + graph ----------
    def draw_graph(ax, title, edges):
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.set_xlim(0, n + 1)
        ax.set_ylim(0, n + 1)
        ax.set_xticks([])
        ax.set_yticks([])

        # grid lines
        for k in range(1, n + 1):
            ax.axhline(k + 0.0, color="lightgray", linewidth=0.5)
            ax.axvline(k + 0.0, color="lightgray", linewidth=0.5)

        # edges
        for a, b in edges:
            x1, y1 = node_pos[a]
            x2, y2 = node_pos[b]
            r = 0.12

            # normalized direction
            dx = x2 - x1
            dy = y2 - y1
            L = (dx * dx + dy * dy) ** 0.5
            if L == 0:
                continue
            ux, uy = dx / L, dy / L

            # start/end shifted outside node
            start = (x1 + ux * r, y1 + uy * r)
            end = (x2 - ux * r, y2 - uy * r)

            ax.annotate(
                "",
                xy=end,
                xytext=start,
                arrowprops=dict(
                    arrowstyle="->",
                    linewidth=0.9,
                    color="blue"
                )
            )

        # nodes
        for name, (x, y) in node_pos.items():
            r = 0.12  # circle radius
            ax.add_patch(
                Circle(
                    (x, y),
                    r,
                    facecolor=colors.get(name, (0.8, 0.8, 0.8)),
                    edgecolor="black",
                )
            )
            # label shifted ~45 degrees outside circle
            dx = r * 1.1
            dy = r * 1.1
            ax.text(x + dx, y + dy, short_label(name), fontsize=8, ha="left", va="bottom")

    draw_graph(ax_h, "Horizontal Constraints $G_H$ (left-of)", edges_h)
    draw_graph(ax_v, "Vertical Constraints $G_V$ (below)", edges_v)

    plt.tight_layout()
    plt.show()

    # ---------- Telemetry back to n8n ----------
    return {
        "success": True,
        "num_blocks": n,
        "num_edges_horizontal": len(edges_h),
        "num_edges_vertical": len(edges_v),
    }


if __name__ == "__main__":
    processor = create_n8n_processor(visualize_sequence_pair)
    processor()
