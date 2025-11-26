#!/usr/bin/env python3
"""
B*-Tree Layout Visualizer for n8n - Fixed Matplotlib Version with Fractal Tree
"""

import sys
import os
import json
import colorsys

# Set matplotlib backend before importing pyplot
import matplotlib

matplotlib.use('TkAgg')  # Use TkAgg backend for Xming compatibility
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

sys.path.append('/mnt/user-data/uploads')
from n8n_json_handler import create_n8n_processor


def generate_distinct_colors(num_colors):
    """Generate distinct colors using HSV"""
    colors = []
    for i in range(num_colors):
        hue = (i * 0.618033988749895) % 1.0  # Golden ratio
        saturation = 0.8 + (i % 3) * 0.1
        value = 0.7 + (i % 2) * 0.2
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
    return colors


def process_bstar_data(json_data):
    """Process and visualize B*-tree data"""

    try:
        # Input validation
        if not json_data:
            return {
                "success": False,
                "error": "Input JSON data is empty",
                "message": "No data provided"
            }

        # Extract data
        data = json_data[0] if isinstance(json_data, list) else json_data

        if not data or 'blocks' not in data or 'bstar_tree' not in data:
            return {
                "success": False,
                "error": "Invalid JSON structure - missing 'blocks' or 'bstar_tree'",
                "message": "Required data fields not found"
            }

        blocks = data['blocks']
        if not blocks:
            return {
                "success": False,
                "error": "No blocks found in data",
                "message": "Empty blocks array"
            }

        blocks_dict = {block['name']: block for block in blocks}
        bstar_tree = data['bstar_tree']

        # Generate colors
        colors = generate_distinct_colors(len(blocks_dict))
        block_colors = {list(blocks_dict.keys())[i]: colors[i] for i in range(len(blocks_dict))}

        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('B*-Tree Layout Visualization', fontsize=16)

        # Left: Block placement (square canvas based on optimization_results)
        ax1.set_title('Block Placement')
        ax1.set_aspect('equal')

        # Get dimensions from optimization_results for square canvas
        if 'optimization_results' in data:
            opt_results = data['optimization_results']
            placement_width = opt_results.get('placement_width', 10)
            placement_height = opt_results.get('placement_height', 10)
            # Use the larger dimension to make it square
            max_dimension = max(placement_width, placement_height)
        else:
            # Fallback to placement_info if optimization_results not available
            placement_info = bstar_tree['placement_info']
            total_width = placement_info['total_width']
            total_height = placement_info['total_height']
            max_dimension = max(total_width, total_height)

        # Set square limits with small margin
        margin = max_dimension * 0.05  # 5% margin
        ax1.set_xlim(-margin, max_dimension + margin)
        ax1.set_ylim(-margin, max_dimension + margin)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')

        def draw_blocks(node):
            if not node or 'name' not in node:
                return

            x_min, y_min = node['x_min'], node['y_min']
            width = node['x_max'] - node['x_min']
            height = node['y_max'] - node['y_min']

            color = block_colors.get(node['name'], '#CCCCCC')
            rect = Rectangle((x_min, y_min), width, height,
                             facecolor=color, edgecolor='black', alpha=0.8)
            ax1.add_patch(rect)

            ax1.text(x_min + width / 2, y_min + height / 2, node['name'],
                     ha='center', va='center', fontweight='bold')

            if 'x_child' in node and node['x_child']:
                draw_blocks(node['x_child'])
            if 'y_child' in node and node['y_child']:
                draw_blocks(node['y_child'])

        draw_blocks(bstar_tree['root'])

        # Right: Tree structure with adjustable fractal spacing
        ax2.set_title('B*-Tree Structure')
        ax2.set_aspect('equal')
        ax2.axis('off')

        positions = {}
        node_depths = {}  # Track depth of each node

        # Adjustable fractal spacing parameters
        FRACTAL_MULTIPLIER = 1.5  # Controls spacing reduction per level (lower = gentler fractal)
        BASE_SPACING = 1.0  # Initial spacing at root level

        # Adaptive node sizing parameters (easily adjustable)
        # Formula: size_at_depth = BASE_SIZE * (DECAY_RATE ^ (depth - 1))
        # Example with NODE_DECAY_RATE=0.80: L1=0.08, L2=0.064, L3=0.051, L7=0.021
        BASE_NODE_RADIUS = 0.1  # Starting radius at root node (level 1)
        NODE_DECAY_RATE = 0.80  # Size multiplier per level (0.80 = 20% smaller each level)
        BASE_FONT_SIZE = 14  # Starting font size at root
        FONT_DECAY_RATE = 0.85  # Font size multiplier per level

        def calc_positions(node, level=1, v_offset=0, h_offset=0):
            if not node or 'name' not in node:
                return v_offset

            positions[node['name']] = (h_offset, v_offset)
            node_depths[node['name']] = level  # Track depth for sizing

            # Calculate spacing: BASE_SPACING / (FRACTAL_MULTIPLIER^(level-1))
            spacing = BASE_SPACING / (FRACTAL_MULTIPLIER ** (level - 1))

            current_v_offset = v_offset

            if 'x_child' in node and node['x_child']:
                calc_positions(node['x_child'], level + 1, current_v_offset, h_offset + spacing)

            if 'y_child' in node and node['y_child']:
                current_v_offset += spacing
                calc_positions(node['y_child'], level + 1, current_v_offset, h_offset)

            return current_v_offset

        calc_positions(bstar_tree['root'])

        # Draw connections FIRST (behind nodes) with arrows and colors
        def draw_connections(node):
            if not node or 'name' not in node or node['name'] not in positions:
                return

            px, py = positions[node['name']]
            parent_depth = node_depths[node['name']]
            parent_radius = BASE_NODE_RADIUS * (NODE_DECAY_RATE ** (parent_depth - 1))

            if 'x_child' in node and node['x_child'] and 'name' in node['x_child']:
                child_name = node['x_child']['name']
                if child_name in positions:
                    cx, cy = positions[child_name]
                    child_depth = node_depths[child_name]
                    child_radius = BASE_NODE_RADIUS * (NODE_DECAY_RATE ** (child_depth - 1))

                    dx, dy = cx - px, cy - py
                    length = (dx ** 2 + dy ** 2) ** 0.5
                    if length > 0:
                        start_x = px + (dx / length) * parent_radius
                        start_y = py + (dy / length) * parent_radius
                        end_x = cx - (dx / length) * child_radius
                        end_y = cy - (dy / length) * child_radius
                        ax2.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                                     arrowprops=dict(arrowstyle='->', color='blue', lw=2))
                draw_connections(node['x_child'])

            if 'y_child' in node and node['y_child'] and 'name' in node['y_child']:
                child_name = node['y_child']['name']
                if child_name in positions:
                    cx, cy = positions[child_name]
                    child_depth = node_depths[child_name]
                    child_radius = BASE_NODE_RADIUS * (NODE_DECAY_RATE ** (child_depth - 1))

                    dx, dy = cx - px, cy - py
                    length = (dx ** 2 + dy ** 2) ** 0.5
                    if length > 0:
                        start_x = px + (dx / length) * parent_radius
                        start_y = py + (dy / length) * parent_radius
                        end_x = cx - (dx / length) * child_radius
                        end_y = cy - (dy / length) * child_radius
                        ax2.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                                     arrowprops=dict(arrowstyle='->', color='green', lw=2))
                draw_connections(node['y_child'])

        draw_connections(bstar_tree['root'])

        # Draw nodes AFTER connections (in front of connections)
        for name, (x, y) in positions.items():
            depth = node_depths[name]
            node_radius = BASE_NODE_RADIUS * (NODE_DECAY_RATE ** (depth - 1))
            font_size = BASE_FONT_SIZE * (FONT_DECAY_RATE ** (depth - 1))

            color = block_colors.get(name, '#CCCCCC')
            circle = Circle((x, y), node_radius, facecolor=color, edgecolor='black', linewidth=1.5)
            ax2.add_patch(circle)
            ax2.text(x, y, name.replace('BLOCK_', ''), ha='center', va='center',
                     fontweight='bold', fontsize=max(5, int(font_size)))

        if positions:
            min_x = min(pos[0] for pos in positions.values())
            max_x = max(pos[0] for pos in positions.values())
            min_y = min(pos[1] for pos in positions.values())
            max_y = max(pos[1] for pos in positions.values())
            margin = 0.2
            ax2.set_xlim(min_x - margin, max_x + margin)
            ax2.set_ylim(min_y - margin, max_y + margin)

        plt.tight_layout()
        plt.show()  # This blocks until window closed

        # Return result after window closes
        result = {
            "success": True,
            "message": "Visualization completed",
            "blocks_count": len(blocks_dict),
            "colors_generated": len(block_colors)
        }

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Visualization failed"
        }


if __name__ == "__main__":
    processor = create_n8n_processor(process_bstar_data)
    processor()