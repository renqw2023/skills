import random

class BinPackingEvaluator:
    """
    A reference evaluator for the 'Algorithm Hunter' benchmark.
    Problem: 3D Bin Packing.
    Goal: Minimize the number of bins used to pack a given stream of items.
    """

    def __init__(self, seed=42):
        self.seed = seed
        self.test_cases = self._generate_test_cases()

    def _generate_test_cases(self, n=100):
        """Generates 100 random packing scenarios."""
        random.seed(self.seed)
        cases = []
        for _ in range(n):
            bin_size = (10, 10, 10)
            items = []
            for _ in range(50): # 50 items per case
                w = random.randint(1, 5)
                h = random.randint(1, 5)
                d = random.randint(1, 5)
                items.append((w, h, d))
            cases.append({"bin_size": bin_size, "items": items})
        return cases

    def evaluate(self, heuristic_func):
        """
        Runs the agent's heuristic function against the test set.
        heuristic_func(items, bin_size) -> list of bins
        """
        total_bins = 0
        total_volume_utilization = 0

        for case in self.test_cases:
            try:
                # Run the agent's code in a sandbox (conceptually)
                packed_bins = heuristic_func(case["items"], case["bin_size"])
                
                # Verify validity
                if not self._is_valid(packed_bins, case["bin_size"], case["items"]):
                    return {"score": 0, "error": "Invalid packing"}

                total_bins += len(packed_bins)
                
                # Calculate volume efficiency
                items_vol = sum(w*h*d for w,h,d in case["items"])
                bins_vol = len(packed_bins) * (case["bin_size"][0] * case["bin_size"][1] * case["bin_size"][2])
                total_volume_utilization += (items_vol / bins_vol)

            except Exception as e:
                return {"score": 0, "error": str(e)}

        avg_efficiency = total_volume_utilization / len(self.test_cases)
        return {
            "score": avg_efficiency,
            "bins_used": total_bins,
            "status": "SUCCESS"
        }

    def _is_valid(self, packed_bins, bin_dims, original_items):
        """
        Checks if items fit and no overlaps.
        packed_bins: list of bins, where each bin is a list of (item_index, x, y, z) tuples.
        """
        # Track which items were packed to ensure no duplicates/omissions if strict
        # For this challenge, we allow partial packing but penalize it (efficiency score handles volume)
        
        packed_item_indices = set()
        
        for bin_idx, bin_contents in enumerate(packed_bins):
            # Check bin boundaries
            for item_idx, x, y, z in bin_contents:
                if item_idx >= len(original_items):
                    return False # Invalid item index
                
                w, h, d = original_items[item_idx]
                
                # Check boundaries
                if x < 0 or y < 0 or z < 0: return False
                if (x + w) > bin_dims[0] or (y + h) > bin_dims[1] or (z + d) > bin_dims[2]:
                    return False
                
                if item_idx in packed_item_indices:
                    return False # Duplicate item
                packed_item_indices.add(item_idx)

            # Check overlaps within bin (O(N^2) naive check for now, N=50 is small)
            for i in range(len(bin_contents)):
                for j in range(i + 1, len(bin_contents)):
                    idx1, x1, y1, z1 = bin_contents[i]
                    idx2, x2, y2, z2 = bin_contents[j]
                    w1, h1, d1 = original_items[idx1]
                    w2, h2, d2 = original_items[idx2]
                    
                    # AABB Collision Check
                    if (x1 < x2 + w2 and x1 + w1 > x2 and
                        y1 < y2 + h2 and y1 + h1 > y2 and
                        z1 < z2 + d2 and z1 + d1 > z2):
                        return False # Overlap!
                        
        return True

# Example Heuristic (Baseline)
def first_fit_decreasing(items, bin_dims):
    # Sort by volume (biggest first)
    items.sort(key=lambda x: x[0]*x[1]*x[2], reverse=True)
    bins = [[]] # Start with one bin
    # ... logic ...
    return bins
