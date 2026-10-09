"""Context Preservation & Spatial Grouping Engine for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Groups visually and spatially related items together (e.g. executive name,
job title, email address, phone number in org cards) so downstream PII detection
retains full contextual co-occurrence.
"""

from __future__ import annotations
from typing import List, Dict, Set
import math
from .schema import ExtractedBlock, Position


class ContextGroupingEngine:
    """Clusters adjacent or structurally related slide blocks into coherent context groups."""

    def __init__(
        self,
        max_vertical_gap_pt: float = 45.0,
        max_horizontal_gap_pt: float = 60.0,
    ):
        self.max_vertical_gap_pt = max_vertical_gap_pt
        self.max_horizontal_gap_pt = max_horizontal_gap_pt

    def are_spatially_proximate(self, p1: Position, p2: Position) -> bool:
        """Check if two positions are close enough to represent a single visual card/group."""
        # Calculate horizontal overlap or distance
        h_overlap = min(p1.left + p1.width, p2.left + p2.width) - max(p1.left, p2.left)
        h_dist = max(0.0, max(p1.left, p2.left) - min(p1.left + p1.width, p2.left + p2.width))

        # Calculate vertical gap
        v_overlap = min(p1.top + p1.height, p2.top + p2.height) - max(p1.top, p2.top)
        v_dist = max(0.0, max(p1.top, p2.top) - min(p1.top + p1.height, p2.top + p2.height))

        # Case 1: Stacked vertically (e.g. Name on top, Title in middle, Email below)
        if h_overlap > 0 or abs(p1.left - p2.left) < self.max_horizontal_gap_pt:
            if v_dist <= self.max_vertical_gap_pt:
                return True

        # Case 2: Side-by-side closely on the same line
        if v_overlap > 0 or abs(p1.top - p2.top) < 20.0:
            if h_dist <= 35.0:
                return True

        return False

    def group_slide_blocks(self, slide_num: int, blocks: List[ExtractedBlock]) -> Dict[str, List[ExtractedBlock]]:
        """Cluster slide blocks into context groups using structural tags and spatial proximity."""
        if not blocks:
            return {}

        n = len(blocks)
        adj: Dict[int, Set[int]] = {i: set() for i in range(n)}

        # Build adjacency graph
        for i in range(n):
            b1 = blocks[i]

            # Speaker notes are always isolated
            if b1.block_type == "speaker_notes":
                continue

            for j in range(i + 1, n):
                b2 = blocks[j]
                if b2.block_type == "speaker_notes":
                    continue

                # 1. Structural rule: Shared parent group shape
                if b1.parent_group_id and b1.parent_group_id == b2.parent_group_id:
                    adj[i].add(j)
                    adj[j].add(i)
                    continue

                # 2. Structural rule: Table cells on the same row
                if b1.table_metadata and b2.table_metadata:
                    if (
                        b1.table_metadata.get("table_index") == b2.table_metadata.get("table_index")
                        and b1.table_metadata.get("row") == b2.table_metadata.get("row")
                    ):
                        adj[i].add(j)
                        adj[j].add(i)
                        continue
                    else:
                        continue  # Cells from different rows or tables are not grouped spatially

                # 3. Titles generally stand alone
                if b1.block_type == "title" or b2.block_type == "title":
                    continue

                # 4. Spatial proximity clustering for body shapes
                if self.are_spatially_proximate(b1.position, b2.position):
                    adj[i].add(j)
                    adj[j].add(i)

        # Find connected components via BFS
        visited: Set[int] = set()
        clusters: List[List[ExtractedBlock]] = []

        for i in range(n):
            if i not in visited:
                queue = [i]
                visited.add(i)
                component: List[ExtractedBlock] = []

                while queue:
                    curr = queue.pop(0)
                    component.append(blocks[curr])
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                clusters.append(component)

        # Assign formatted context_group_id to blocks and index map
        grouped_result: Dict[str, List[ExtractedBlock]] = {}
        for idx, cluster in enumerate(clusters, start=1):
            ctx_id = f"slide_{slide_num}_group_{idx:02d}"
            for block in cluster:
                block.context_group_id = ctx_id
            grouped_result[ctx_id] = cluster

        return grouped_result

    def process_all_blocks(self, blocks: List[ExtractedBlock]) -> Dict[str, List[str]]:
        """Process all presentation blocks by slide and return context_group_id -> [block_ids] map."""
        slides_map: Dict[int, List[ExtractedBlock]] = {}
        for b in blocks:
            slides_map.setdefault(b.slide, []).append(b)

        all_groups_map: Dict[str, List[str]] = {}

        for slide_num, slide_blocks in slides_map.items():
            groups = self.group_slide_blocks(slide_num, slide_blocks)
            for ctx_id, blk_list in groups.items():
                all_groups_map[ctx_id] = [b.block_id for b in blk_list]

        return all_groups_map
