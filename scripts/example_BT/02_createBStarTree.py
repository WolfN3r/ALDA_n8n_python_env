#!/usr/bin/env python3
"""
B* Tree Generator for Module Placement
Creates B*-tree structure with contour-based placement from JSON device data
"""

import json
import sys
import gc


class BStarTreeNode:
    """Node in the B*-tree structure"""

    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
        self.x_min = 0.0
        self.y_min = 0.0
        self.x_max = width
        self.y_max = height
        self.x_child = None  # Right child (placed to the right)
        self.y_child = None  # Up child (placed above)

    def to_dict(self):
        """Convert node to dictionary format"""
        result = {
            "name": self.name,
            "x_min": round(self.x_min, 2),
            "y_min": round(self.y_min, 2),
            "x_max": round(self.x_max, 2),
            "y_max": round(self.y_max, 2),
            "x_child": self.x_child.to_dict() if self.x_child else {},
            "y_child": self.y_child.to_dict() if self.y_child else {}
        }
        return result


class ContourStructure:
    """Maintains contour for placement"""

    def __init__(self):
        self.contour = []  # List of (x_start, x_end, y_top) tuples

    def find_y_position(self, x_start, x_end):
        """Find the y position where block can be placed"""
        max_y = 0.0
        for c_start, c_end, c_top in self.contour:
            if not (x_end <= c_start or x_start >= c_end):
                max_y = max(max_y, c_top)
        return max_y

    def update_contour(self, x_start, x_end, y_top):
        """Update contour after placing a block"""
        new_contour = []
        for c_start, c_end, c_top in self.contour:
            if c_end <= x_start or c_start >= x_end:
                new_contour.append((c_start, c_end, c_top))
            elif c_start < x_start and c_end > x_end:
                new_contour.append((c_start, x_start, c_top))
                new_contour.append((x_end, c_end, c_top))
            elif c_start < x_start:
                new_contour.append((c_start, x_start, c_top))
            elif c_end > x_end:
                new_contour.append((x_end, c_end, c_top))

        new_contour.append((x_start, x_end, y_top))
        new_contour.sort()
        self.contour = self._merge_segments(new_contour)

    def _merge_segments(self, segments):
        """Merge adjacent segments with same height"""
        if not segments:
            return []

        merged = [segments[0]]
        for start, end, height in segments[1:]:
            last_start, last_end, last_height = merged[-1]
            if start == last_end and height == last_height:
                merged[-1] = (last_start, end, height)
            else:
                merged.append((start, end, height))
        return merged


class BStarTreeGenerator:
    """Generates B*-tree structure with placement"""

    def __init__(self, blocks_data):
        self.blocks = self._extract_default_blocks(blocks_data)
        self.contour = ContourStructure()
        self.placed_blocks = {}

    def _extract_default_blocks(self, blocks_data):
        """Extract blocks with default variant dimensions"""
        blocks = {}
        for block in blocks_data:
            name = block["name"]
            default_variant = None
            for variant in block["variants"]:
                if variant.get("is_default", False):
                    default_variant = variant
                    break

            if default_variant:
                blocks[name] = {
                    "width": default_variant["width"],
                    "height": default_variant["height"],
                    "device_type": block.get("device_type", ""),
                    "symmetry": block.get("symmetry", {})
                }
        return blocks

    def generate_bstar_tree(self):
        """Generate B*-tree with balanced depth"""
        if not self.blocks:
            return None

        sorted_blocks = sorted(self.blocks.items(),
                               key=lambda x: x[1]["width"] * x[1]["height"],
                               reverse=True)

        root_name, root_data = sorted_blocks[0]
        root = BStarTreeNode(root_name, root_data["width"], root_data["height"])
        root.x_min = 0.0
        root.y_min = 0.0
        root.x_max = root.width
        root.y_max = root.height

        self.contour.update_contour(root.x_min, root.x_max, root.y_max)
        self.placed_blocks[root_name] = root

        remaining_blocks = sorted_blocks[1:]
        nodes_queue = [root]

        while remaining_blocks and nodes_queue:
            current_level_size = len(nodes_queue)

            for _ in range(current_level_size):
                if not remaining_blocks:
                    break

                current_node = nodes_queue.pop(0)

                if remaining_blocks and current_node.x_child is None:
                    child_name, child_data = remaining_blocks.pop(0)
                    x_child = self._place_x_child(current_node, child_name, child_data)
                    if x_child:
                        current_node.x_child = x_child
                        nodes_queue.append(x_child)

                if remaining_blocks and current_node.y_child is None:
                    child_name, child_data = remaining_blocks.pop(0)
                    y_child = self._place_y_child(current_node, child_name, child_data)
                    if y_child:
                        current_node.y_child = y_child
                        nodes_queue.append(y_child)

        return root

    def _place_x_child(self, parent, child_name, child_data):
        """Place x_child (right child) of parent node"""
        child = BStarTreeNode(child_name, child_data["width"], child_data["height"])

        child.x_min = parent.x_max
        child.x_max = child.x_min + child.width
        child.y_min = self.contour.find_y_position(child.x_min, child.x_max)
        child.y_max = child.y_min + child.height

        self.contour.update_contour(child.x_min, child.x_max, child.y_max)
        self.placed_blocks[child_name] = child
        return child

    def _place_y_child(self, parent, child_name, child_data):
        """Place y_child (up child) of parent node"""
        child = BStarTreeNode(child_name, child_data["width"], child_data["height"])

        child.x_min = parent.x_min
        child.x_max = child.x_min + child.width
        min_y_from_parent = parent.y_max
        min_y_from_contour = self.contour.find_y_position(child.x_min, child.x_max)
        child.y_min = max(min_y_from_parent, min_y_from_contour)
        child.y_max = child.y_min + child.height

        self.contour.update_contour(child.x_min, child.x_max, child.y_max)
        self.placed_blocks[child_name] = child
        return child


def process_bstar_tree(json_data):
    """Process JSON data and create B*-tree structure"""
    try:
        if "blocks" not in json_data:
            return {"error": "No blocks found in JSON data"}

        generator = BStarTreeGenerator(json_data["blocks"])
        root_node = generator.generate_bstar_tree()

        if root_node is None:
            return {"error": "Failed to generate B*-tree structure"}

        result = json_data.copy()
        result["bstar_tree"] = {
            "root": root_node.to_dict(),
            "placement_info": {
                "total_blocks": len(generator.placed_blocks),
                "total_width": max(block.x_max for block in generator.placed_blocks.values()),
                "total_height": max(block.y_max for block in generator.placed_blocks.values()),
                "placement_method": "contour_based_bstar_tree"
            }
        }

        return result

    except Exception as e:
        return {"error": f"Failed to create B*-tree: {str(e)}"}


def main():
    """Main function for n8n integration"""
    try:
        # Read UTF-8 encoded JSON from n8n
        input_bytes = sys.stdin.buffer.read()
        input_text = input_bytes.decode('utf-8', errors='replace')
        json_data = json.loads(input_text)

        # Process the data
        result = process_bstar_tree(json_data)

        # Output UTF-8 encoded JSON back to n8n
        output_text = json.dumps(result, ensure_ascii=False, separators=(',', ':'))
        print(output_text)

        # Cleanup
        del json_data, result
        gc.collect()

    except Exception as e:
        error_response = {"error": f"Processing failed: {str(e)}"}
        print(json.dumps(error_response, ensure_ascii=False))


if __name__ == "__main__":
    main()