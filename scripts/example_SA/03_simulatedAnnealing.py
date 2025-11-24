#!/usr/bin/env python3
"""
Robust B*-tree Simulated Annealing Optimizer
"""

import json
import random
import math
from n8n_json_handler import create_n8n_processor

# OPTIMIZATION SETTINGS
INITIAL_TEMP = 1000.0
FINAL_TEMP = 0.1
COOLING_RATE = 0.95
MAX_ITERATIONS = 500
AREA_WEIGHT = 100.0
DEAD_SPACE_WEIGHT = 10.0
ASPECT_RATIO_WEIGHT = 10.0
TARGET_ASPECT_RATIO = 1.0
MAX_ASPECT_RATIO = 2.0
ASPECT_PENALTY = 1000.0


class SimpleOptimizer:
    """Simplified optimizer with robust error handling"""

    def __init__(self, json_data):
        self.data = json_data
        self.variants = self._get_variants()
        self.actual_iterations = 0

    def _get_variants(self):
        """Extract block variants safely"""
        variants = {}
        try:
            for block in self.data.get("blocks", []):
                name = block["name"]
                variants[name] = []
                for variant in block["variants"]:
                    variants[name].append({
                        "width": float(variant["width"]),
                        "height": float(variant["height"])
                    })
        except:
            pass
        return variants

    def _get_all_nodes_from_dict(self, node_dict, nodes_list=None):
        """Safely get all nodes from dict tree"""
        if nodes_list is None:
            nodes_list = []

        if not node_dict or not isinstance(node_dict, dict):
            return nodes_list

        if "name" in node_dict:
            nodes_list.append(node_dict)

        # Recursively get children
        x_child = node_dict.get("x_child", {})
        y_child = node_dict.get("y_child", {})

        if x_child:
            self._get_all_nodes_from_dict(x_child, nodes_list)
        if y_child:
            self._get_all_nodes_from_dict(y_child, nodes_list)

        return nodes_list

    def _safe_copy_tree(self, tree_dict):
        """Safe tree copying without deepcopy"""
        if not tree_dict or not isinstance(tree_dict, dict):
            return {}

        try:
            return {
                "name": tree_dict.get("name", ""),
                "x_min": float(tree_dict.get("x_min", 0)),
                "y_min": float(tree_dict.get("y_min", 0)),
                "x_max": float(tree_dict.get("x_max", 0)),
                "y_max": float(tree_dict.get("y_max", 0)),
                "x_child": self._safe_copy_tree(tree_dict.get("x_child", {})),
                "y_child": self._safe_copy_tree(tree_dict.get("y_child", {}))
            }
        except:
            return tree_dict

    def _op1_change_variant(self, tree_dict):
        """Op1: Change variant safely"""
        try:
            nodes = self._get_all_nodes_from_dict(tree_dict)
            if not nodes:
                return tree_dict

            node = random.choice(nodes)
            name = node.get("name", "")

            if name in self.variants and len(self.variants[name]) > 1:
                variant = random.choice(self.variants[name])
                width = variant["width"]
                height = variant["height"]

                node["x_max"] = node["x_min"] + width
                node["y_max"] = node["y_min"] + height

        except:
            pass  # Return original tree if error

        return tree_dict

    def _op2_swap_nodes(self, tree_dict):
        """Op2: Swap node data safely"""
        try:
            nodes = self._get_all_nodes_from_dict(tree_dict)
            if len(nodes) < 2:
                return tree_dict

            node1, node2 = random.sample(nodes, 2)

            # Simple swap of names and dimensions
            name1 = node1.get("name", "")
            name2 = node2.get("name", "")

            width1 = node1.get("x_max", 0) - node1.get("x_min", 0)
            height1 = node1.get("y_max", 0) - node1.get("y_min", 0)
            width2 = node2.get("x_max", 0) - node2.get("x_min", 0)
            height2 = node2.get("y_max", 0) - node2.get("y_min", 0)

            node1["name"] = name2
            node2["name"] = name1

            node1["x_max"] = node1["x_min"] + width2
            node1["y_max"] = node1["y_min"] + height2
            node2["x_max"] = node2["x_min"] + width1
            node2["y_max"] = node2["y_min"] + height1

        except:
            pass

        return tree_dict

    def _contour_placement(self, tree_dict):
        """Contour-based placement for better packing"""
        try:
            # Reset contour
            contour = []  # List of (x_start, x_end, y_top)

            # Place root at origin
            root = tree_dict
            if root and "name" in root:
                width = root.get("x_max", 0) - root.get("x_min", 0)
                height = root.get("y_max", 0) - root.get("y_min", 0)

                root["x_min"] = 0.0
                root["y_min"] = 0.0
                root["x_max"] = width
                root["y_max"] = height

                contour = [(0.0, width, height)]

                # Place other nodes using contour
                self._place_children_with_contour(root, contour)

        except:
            pass

        return tree_dict

    def _place_children_with_contour(self, node, contour):
        """Recursively place children using contour"""
        try:
            # Place x_child (right of current node)
            if node.get("x_child") and "name" in node["x_child"]:
                child = node["x_child"]
                width = child.get("x_max", 0) - child.get("x_min", 0)
                height = child.get("y_max", 0) - child.get("y_min", 0)

                # Position x_child to the right
                child["x_min"] = node.get("x_max", 0)
                child["y_min"] = self._find_y_from_contour(contour, child["x_min"], child["x_min"] + width)
                child["x_max"] = child["x_min"] + width
                child["y_max"] = child["y_min"] + height

                # Update contour
                self._update_contour(contour, child["x_min"], child["x_max"], child["y_max"])
                self._place_children_with_contour(child, contour)

            # Place y_child (above current node, same x)
            if node.get("y_child") and "name" in node["y_child"]:
                child = node["y_child"]
                width = child.get("x_max", 0) - child.get("x_min", 0)
                height = child.get("y_max", 0) - child.get("y_min", 0)

                # Position y_child above with same x
                child["x_min"] = node.get("x_min", 0)
                y_from_contour = self._find_y_from_contour(contour, child["x_min"], child["x_min"] + width)
                child["y_min"] = max(node.get("y_max", 0), y_from_contour)
                child["x_max"] = child["x_min"] + width
                child["y_max"] = child["y_min"] + height

                # Update contour
                self._update_contour(contour, child["x_min"], child["x_max"], child["y_max"])
                self._place_children_with_contour(child, contour)

        except:
            pass

    def _find_y_from_contour(self, contour, x_start, x_end):
        """Find Y position from contour"""
        max_y = 0.0
        try:
            for c_start, c_end, c_top in contour:
                # Check overlap in x direction
                if not (x_end <= c_start or x_start >= c_end):
                    max_y = max(max_y, c_top)
        except:
            pass
        return max_y

    def _update_contour(self, contour, x_start, x_end, y_top):
        """Update contour after placing block"""
        try:
            new_contour = []

            # Remove overlapped segments and keep non-overlapping ones
            for c_start, c_end, c_top in contour:
                if c_end <= x_start or c_start >= x_end:
                    # No overlap, keep segment
                    new_contour.append((c_start, c_end, c_top))
                elif c_start < x_start and c_end > x_end:
                    # Split segment
                    new_contour.append((c_start, x_start, c_top))
                    new_contour.append((x_end, c_end, c_top))
                elif c_start < x_start:
                    # Keep left part
                    new_contour.append((c_start, x_start, c_top))
                elif c_end > x_end:
                    # Keep right part
                    new_contour.append((x_end, c_end, c_top))

            # Add new segment
            new_contour.append((x_start, x_end, y_top))
            new_contour.sort()

            # Update original contour
            contour.clear()
            contour.extend(new_contour)

        except:
            pass

    def _calculate_fitness(self, tree_dict):
        """Calculate fitness with area, aspect ratio, and dead space"""
        try:
            # Use contour placement instead of simple grid
            self._contour_placement(tree_dict)
            nodes = self._get_all_nodes_from_dict(tree_dict)

            if not nodes:
                return 999999

            # Calculate bounding rectangle
            max_x = max(node.get("x_max", 0) for node in nodes)
            max_y = max(node.get("y_max", 0) for node in nodes)

            if max_x <= 0 or max_y <= 0:
                return 999999

            # Calculate total area and actual used area
            total_area = max_x * max_y
            used_area = sum((node.get("x_max", 0) - node.get("x_min", 0)) *
                            (node.get("y_max", 0) - node.get("y_min", 0)) for node in nodes)

            # Dead space (empty space between blocks)
            dead_space = total_area - used_area
            dead_space_ratio = dead_space / total_area if total_area > 0 else 0

            # Aspect ratio penalty
            aspect_ratio = max(max_x, max_y) / min(max_x, max_y)

            if aspect_ratio > MAX_ASPECT_RATIO:
                aspect_penalty = ASPECT_PENALTY * (aspect_ratio - MAX_ASPECT_RATIO)
            else:
                aspect_penalty = abs(aspect_ratio - TARGET_ASPECT_RATIO) * ASPECT_RATIO_WEIGHT

            # Combined fitness: area + aspect penalty + dead space penalty
            dead_space_penalty = dead_space_ratio * DEAD_SPACE_WEIGHT  # Weight for dead space
            fitness = total_area * AREA_WEIGHT + aspect_penalty + dead_space_penalty

            return fitness

        except:
            return 999999

    def optimize(self):
        """Run simplified simulated annealing"""
        try:
            # Get initial tree
            current_tree = self.data.get("bstar_tree", {}).get("root", {})
            if not current_tree:
                return None, 999999, 0

            current_fitness = self._calculate_fitness(current_tree)
            best_tree = self._safe_copy_tree(current_tree)
            best_fitness = current_fitness

            temperature = INITIAL_TEMP

            for iteration in range(MAX_ITERATIONS):
                self.actual_iterations = iteration + 1

                if temperature < FINAL_TEMP:
                    break

                # Create new solution
                new_tree = self._safe_copy_tree(current_tree)

                # Choose operation
                rand_val = random.random()
                if rand_val < 0.4:
                    new_tree = self._op1_change_variant(new_tree)
                elif rand_val < 0.8:
                    new_tree = self._op2_swap_nodes(new_tree)
                else:
                    # Skip Op3 for now to avoid tree corruption
                    new_tree = self._op1_change_variant(new_tree)

                new_fitness = self._calculate_fitness(new_tree)

                # Accept or reject
                if new_fitness < current_fitness:
                    current_tree = new_tree
                    current_fitness = new_fitness

                    if new_fitness < best_fitness:
                        best_tree = self._safe_copy_tree(new_tree)
                        best_fitness = new_fitness
                else:
                    delta = new_fitness - current_fitness
                    if temperature > 0:
                        prob = math.exp(-delta / temperature)
                        if random.random() < prob:
                            current_tree = new_tree
                            current_fitness = new_fitness

                temperature *= COOLING_RATE

            return best_tree, best_fitness, self.actual_iterations

        except Exception as e:
            return None, 999999, self.actual_iterations


def optimize_bstar_tree_safe(json_data):
    """
    Safe optimizer with comprehensive error handling
    """
    # Immediate validation
    if not json_data or not isinstance(json_data, dict):
        return {"error": "Invalid input data"}

    if "bstar_tree" not in json_data:
        return {"error": "No bstar_tree in input"}

    if "blocks" not in json_data:
        return {"error": "No blocks in input"}

    try:
        optimizer = SimpleOptimizer(json_data)
        best_tree, best_fitness, iterations = optimizer.optimize()

        if best_tree is None:
            return {"error": "Optimization failed"}

        # Calculate final metrics safely
        optimizer._contour_placement(best_tree)
        nodes = optimizer._get_all_nodes_from_dict(best_tree)

        if not nodes:
            return {"error": "No nodes in result"}

        max_x = max(node.get("x_max", 0) for node in nodes)
        max_y = max(node.get("y_max", 0) for node in nodes)
        total_area = max_x * max_y
        used_area = sum((node.get("x_max", 0) - node.get("x_min", 0)) *
                        (node.get("y_max", 0) - node.get("y_min", 0)) for node in nodes)
        dead_space = total_area - used_area
        dead_space_ratio = (dead_space / total_area * 100) if total_area > 0 else 0
        aspect_ratio = max(max_x, max_y) / min(max_x, max_y) if min(max_x, max_y) > 0 else 1.0

        # Build result
        result = dict(json_data)  # Safe copy
        result["bstar_tree"] = {"root": best_tree}
        result["optimization_results"] = {
            "fitness_function": round(best_fitness, 2),
            "total_area": round(total_area, 2),
            "used_area": round(used_area, 2),
            "dead_space": round(dead_space, 2),
            "dead_space_percentage": round(dead_space_ratio, 2),
            "aspect_ratio": round(aspect_ratio, 2),
            "placement_width": round(max_x, 2),
            "placement_height": round(max_y, 2),
            "actual_iterations": iterations,
            "optimization_method": "simulated_annealing_contour"
        }

        return result

    except Exception as e:
        return {"error": f"Optimization error: {str(e)}"}


if __name__ == "__main__":
    processor = create_n8n_processor(optimize_bstar_tree_safe)
    processor()