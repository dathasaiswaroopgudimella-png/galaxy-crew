import heapq
import logging
import numpy as np
from typing import List, Tuple, Dict, Set, Optional
from phse.models import RasterLayer

logger = logging.getLogger("phse")

class RoverPathfinder:
    """
    Computes optimal rover traversal paths on lunar surface grids using A* pathfinding.
    Calculates cumulative costs based on slope safety, terrain roughness, and distance.
    """
    def __init__(
        self,
        max_rover_slope: float = 20.0,
        slope_cost_factor: float = 2.0,
        roughness_cost_factor: float = 5.0
    ):
        self.max_rover_slope = max_rover_slope
        self.slope_cost_factor = slope_cost_factor
        self.roughness_cost_factor = roughness_cost_factor

    def _get_neighbors(self, y: int, x: int, height: int, width: int) -> List[Tuple[int, int, float]]:
        """
        Returns list of 8-connected neighbors with step distances (1.0 for straight, 1.414 for diagonal).
        """
        neighbors = []
        # Directions: (dy, dx, step_dist)
        directions = [
            (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
            (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)
        ]
        
        for dy, dx, dist in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width:
                neighbors.append((ny, nx, dist))
                
        return neighbors

    def _heuristic(self, y1: int, x1: int, y2: int, x2: int) -> float:
        """
        Octile distance heuristic for 8-connected grid search.
        """
        dy = abs(y1 - y2)
        dx = abs(x1 - x2)
        return max(dy, dx) + (1.414 - 1.0) * min(dy, dx)

    def find_path(
        self,
        slope_layer: RasterLayer,
        roughness_layer: RasterLayer,
        start_x: int,
        start_y: int,
        goal_x: int,
        goal_y: int
    ) -> List[Tuple[int, int]]:
        """
        Calculates the optimal safety-constrained path from start to goal.
        
        Returns:
            List[Tuple[int, int]]: List of (x, y) coordinates representing the path.
                                  Returns empty list if no path exists.
        """
        logger.info(f"Computing rover traversal path from ({start_x}, {start_y}) to ({goal_x}, {goal_y})...")
        
        slope = slope_layer.data
        roughness = roughness_layer.data
        nodata = slope_layer.metadata.nodata
        
        height, width = slope.shape
        
        # Priority queue stores tuples of: (f_score, y, x)
        open_set: List[Tuple[float, int, int]] = []
        heapq.heappush(open_set, (0.0, start_y, start_x))
        
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        
        # g_score: actual cost from start to current node
        g_score: Dict[Tuple[int, int], float] = {(start_y, start_x): 0.0}
        
        # Track closed set
        closed_set: Set[Tuple[int, int]] = set()
        
        while open_set:
            _, y, x = heapq.heappop(open_set)
            
            if (y, x) == (goal_y, goal_x):
                # Reconstruct path
                path = []
                current = (y, x)
                while current in came_from:
                    path.append((current[1], current[0])) # Convert back to (x, y)
                    current = came_from[current]
                path.append((start_x, start_y))
                path.reverse()
                logger.info(f"Rover path found with {len(path)} waypoints.")
                return path
                
            if (y, x) in closed_set:
                continue
                
            closed_set.add((y, x))
            
            for ny, nx, step_dist in self._get_neighbors(y, x, height, width):
                if (ny, nx) in closed_set:
                    continue
                    
                # Check for critical slope or nodata boundaries
                s_val = slope[ny, nx]
                r_val = roughness[ny, nx]
                if s_val == nodata or r_val == roughness_layer.metadata.nodata or np.isnan(s_val):
                    continue
                    
                if s_val > self.max_rover_slope:
                    continue # Exceeds climbing limits
                    
                # Compute cost: Step_dist * (1.0 + k_s * slope^2 + k_r * roughness)
                # Average slope/roughness between the two nodes
                avg_slope = (slope[y, x] + s_val) / 2.0
                avg_rough = (roughness[y, x] + r_val) / 2.0
                
                penalty = 1.0 + (self.slope_cost_factor * (avg_slope / 10.0)**2) + (self.roughness_cost_factor * avg_rough)
                edge_cost = step_dist * penalty
                
                tentative_g = g_score[(y, x)] + edge_cost
                
                if (ny, nx) not in g_score or tentative_g < g_score[(ny, nx)]:
                    g_score[(ny, nx)] = tentative_g
                    f_score = tentative_g + self._heuristic(ny, nx, goal_y, goal_x)
                    came_from[(ny, nx)] = (y, x)
                    heapq.heappush(open_set, (f_score, ny, nx))
                    
        logger.warning(f"No traversable path found between ({start_x}, {start_y}) and ({goal_x}, {goal_y}) within slope constraints.")
        return []
