"""
Data lineage tracking service for the Stock Analysis system
"""
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class TransformationType(str, Enum):
    """Types of data transformations"""
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    CALCULATION = "calculation"
    AGGREGATION = "aggregation"
    ENRICHMENT = "enrichment"
    FILTERING = "filtering"


@dataclass
class DataSource:
    """Represents a data source in the lineage"""
    id: str
    name: str
    type: str  # e.g., "api", "database", "file", "calculation"
    location: Optional[str] = None  # URL, file path, table name, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataTransformation:
    """Represents a data transformation step"""
    id: str
    name: str
    transformation_type: TransformationType
    input_sources: List[str]  # Source IDs
    output_source: str  # Output source ID
    parameters: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageNode:
    """A node in the data lineage graph"""
    source: DataSource
    transformations: List[DataTransformation] = field(default_factory=list)
    upstream_nodes: Set[str] = field(default_factory=set)  # Source IDs
    downstream_nodes: Set[str] = field(default_factory=set)  # Source IDs


class DataLineageService:
    """Service for tracking data lineage and transformations"""

    def __init__(self):
        self.sources: Dict[str, DataSource] = {}
        self.transformations: Dict[str, DataTransformation] = {}
        self.lineage_graph: Dict[str, LineageNode] = {}

    def register_source(
        self,
        name: str,
        source_type: str,
        location: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None
    ) -> str:
        """Register a new data source"""
        source_id = source_id or str(uuid.uuid4())

        source = DataSource(
            id=source_id,
            name=name,
            type=source_type,
            location=location,
            metadata=metadata or {}
        )

        self.sources[source_id] = source
        self.lineage_graph[source_id] = LineageNode(source=source)

        logger.info(f"Registered data source: {name} ({source_id})")
        return source_id

    def record_transformation(
        self,
        name: str,
        transformation_type: TransformationType,
        input_source_ids: List[str],
        output_source_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        transformation_id: Optional[str] = None
    ) -> str:
        """Record a data transformation"""
        transformation_id = transformation_id or str(uuid.uuid4())

        # Validate input sources exist
        for source_id in input_source_ids:
            if source_id not in self.sources:
                raise ValueError(f"Input source {source_id} not found")

        # Validate output source exists
        if output_source_id not in self.sources:
            raise ValueError(f"Output source {output_source_id} not found")

        transformation = DataTransformation(
            id=transformation_id,
            name=name,
            transformation_type=transformation_type,
            input_sources=input_source_ids,
            output_source=output_source_id,
            parameters=parameters or {},
            execution_time_ms=execution_time_ms,
            metadata=metadata or {}
        )

        self.transformations[transformation_id] = transformation

        # Update lineage graph
        output_node = self.lineage_graph[output_source_id]
        output_node.transformations.append(transformation)

        for input_source_id in input_source_ids:
            # Add upstream relationship
            output_node.upstream_nodes.add(input_source_id)
            # Add downstream relationship
            input_node = self.lineage_graph[input_source_id]
            input_node.downstream_nodes.add(output_source_id)

        logger.info(f"Recorded transformation: {name} ({transformation_id})")
        return transformation_id

    def trace_lineage_upstream(self, source_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """Trace data lineage upstream from a given source"""
        if source_id not in self.lineage_graph:
            raise ValueError(f"Source {source_id} not found")

        visited = set()
        lineage = {}

        def _trace_upstream(current_id: str, depth: int) -> Dict[str, Any]:
            if depth > max_depth or current_id in visited:
                return {}

            visited.add(current_id)
            node = self.lineage_graph[current_id]

            result = {
                "source": {
                    "id": node.source.id,
                    "name": node.source.name,
                    "type": node.source.type,
                    "location": node.source.location,
                    "created_at": node.source.created_at.isoformat()
                },
                "transformations": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.transformation_type.value,
                        "executed_at": t.executed_at.isoformat(),
                        "execution_time_ms": t.execution_time_ms,
                        "parameters": t.parameters
                    }
                    for t in node.transformations
                ],
                "upstream": {}
            }

            for upstream_id in node.upstream_nodes:
                result["upstream"][upstream_id] = _trace_upstream(upstream_id, depth + 1)

            return result

        return _trace_upstream(source_id, 0)

    def trace_lineage_downstream(self, source_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """Trace data lineage downstream from a given source"""
        if source_id not in self.lineage_graph:
            raise ValueError(f"Source {source_id} not found")

        visited = set()

        def _trace_downstream(current_id: str, depth: int) -> Dict[str, Any]:
            if depth > max_depth or current_id in visited:
                return {}

            visited.add(current_id)
            node = self.lineage_graph[current_id]

            result = {
                "source": {
                    "id": node.source.id,
                    "name": node.source.name,
                    "type": node.source.type,
                    "location": node.source.location,
                    "created_at": node.source.created_at.isoformat()
                },
                "transformations": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.transformation_type.value,
                        "executed_at": t.executed_at.isoformat(),
                        "execution_time_ms": t.execution_time_ms,
                        "parameters": t.parameters
                    }
                    for t in node.transformations
                ],
                "downstream": {}
            }

            for downstream_id in node.downstream_nodes:
                result["downstream"][downstream_id] = _trace_downstream(downstream_id, depth + 1)

            return result

        return _trace_downstream(source_id, 0)

    def get_transformation_path(self, from_source_id: str, to_source_id: str) -> List[str]:
        """Get the transformation path between two sources"""
        if from_source_id not in self.lineage_graph or to_source_id not in self.lineage_graph:
            raise ValueError("Source not found")

        # Simple BFS to find path
        from collections import deque

        queue = deque([(from_source_id, [from_source_id])])
        visited = set()

        while queue:
            current_id, path = queue.popleft()

            if current_id == to_source_id:
                return path

            if current_id in visited:
                continue

            visited.add(current_id)
            node = self.lineage_graph[current_id]

            for downstream_id in node.downstream_nodes:
                if downstream_id not in visited:
                    queue.append((downstream_id, path + [downstream_id]))

        return []  # No path found

    def get_lineage_summary(self) -> Dict[str, Any]:
        """Get a summary of the lineage graph"""
        return {
            "total_sources": len(self.sources),
            "total_transformations": len(self.transformations),
            "source_types": list(set(source.type for source in self.sources.values())),
            "transformation_types": list(set(t.transformation_type.value for t in self.transformations.values())),
            "root_sources": [
                source_id for source_id, node in self.lineage_graph.items()
                if not node.upstream_nodes
            ],
            "leaf_sources": [
                source_id for source_id, node in self.lineage_graph.items()
                if not node.downstream_nodes
            ]
        }

    def validate_lineage_integrity(self) -> List[str]:
        """Validate the integrity of the lineage graph"""
        issues = []

        # Check for orphaned transformations
        for transformation in self.transformations.values():
            for input_id in transformation.input_sources:
                if input_id not in self.sources:
                    issues.append(f"Transformation {transformation.id} references missing input source {input_id}")

            if transformation.output_source not in self.sources:
                issues.append(f"Transformation {transformation.id} references missing output source {transformation.output_source}")

        # Check for circular dependencies
        def has_cycle(source_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(source_id)
            rec_stack.add(source_id)

            node = self.lineage_graph.get(source_id)
            if node:
                for downstream_id in node.downstream_nodes:
                    if downstream_id not in visited:
                        if has_cycle(downstream_id, visited, rec_stack):
                            return True
                    elif downstream_id in rec_stack:
                        return True

            rec_stack.remove(source_id)
            return False

        visited = set()
        for source_id in self.sources:
            if source_id not in visited:
                if has_cycle(source_id, visited, set()):
                    issues.append(f"Circular dependency detected involving source {source_id}")

        return issues
