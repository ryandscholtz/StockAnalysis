"""
Property-based tests for data lineage traceability
Feature: tech-stack-modernization, Property 24: Data Lineage Traceability
"""
import pytest
from hypothesis import given, strategies as st, assume
from typing import Dict, Any, List
from unittest.mock import Mock

from app.services.data_lineage_service import (
    DataLineageService,
    TransformationType,
    DataSource,
    DataTransformation
)


# Test data generators
@st.composite
def data_source_info(draw):
    """Generate data source information"""
    source_types = ["api", "database", "file", "calculation", "external_feed"]
    return {
        "name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))),
        "source_type": draw(st.sampled_from(source_types)),
        "location": draw(st.one_of(
            st.none(),
            st.text(min_size=1, max_size=100)
        )),
        "metadata": draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
            max_size=5
        ))
    }


@st.composite
def transformation_info(draw):
    """Generate transformation information"""
    return {
        "name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))),
        "transformation_type": draw(st.sampled_from(list(TransformationType))),
        "parameters": draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
            max_size=5
        )),
        "execution_time_ms": draw(st.one_of(
            st.none(),
            st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False)
        ))
    }


@st.composite
def lineage_chain(draw):
    """Generate a chain of data sources and transformations"""
    chain_length = draw(st.integers(min_value=2, max_value=6))
    
    sources = []
    transformations = []
    
    # Create sources
    for i in range(chain_length):
        source_info = draw(data_source_info())
        sources.append(source_info)
    
    # Create transformations between consecutive sources
    for i in range(chain_length - 1):
        transform_info = draw(transformation_info())
        transformations.append({
            **transform_info,
            "input_index": i,
            "output_index": i + 1
        })
    
    return sources, transformations


class TestDataLineageTraceability:
    """Test data lineage traceability properties"""
    
    def create_lineage_service(self):
        """Create a fresh lineage service"""
        return DataLineageService()
    
    @given(lineage_chain())
    def test_data_lineage_traceability_property(self, chain_data):
        """
        Property 24: Data Lineage Traceability
        For any data transformation, the lineage information should allow tracing 
        from the final result back to the original source
        **Validates: Requirements 10.5**
        """
        lineage_service = self.create_lineage_service()
        sources, transformations = chain_data
        assume(len(sources) >= 2)  # Need at least 2 sources for a transformation
        
        # Register all sources
        source_ids = []
        for source_info in sources:
            source_id = lineage_service.register_source(**source_info)
            source_ids.append(source_id)
        
        # Record all transformations
        transformation_ids = []
        for transform_info in transformations:
            input_idx = transform_info.pop("input_index")
            output_idx = transform_info.pop("output_index")
            
            transform_id = lineage_service.record_transformation(
                input_source_ids=[source_ids[input_idx]],
                output_source_id=source_ids[output_idx],
                **transform_info
            )
            transformation_ids.append(transform_id)
        
        # Property: Should be able to trace from final result back to original source
        final_source_id = source_ids[-1]
        original_source_id = source_ids[0]
        
        # Test upstream tracing from final result
        upstream_lineage = lineage_service.trace_lineage_upstream(final_source_id)
        
        # Verify the lineage contains the original source
        def contains_source_in_lineage(lineage_data: Dict[str, Any], target_source_id: str) -> bool:
            if lineage_data.get("source", {}).get("id") == target_source_id:
                return True
            
            upstream = lineage_data.get("upstream", {})
            for upstream_lineage in upstream.values():
                if contains_source_in_lineage(upstream_lineage, target_source_id):
                    return True
            
            return False
        
        assert contains_source_in_lineage(upstream_lineage, original_source_id), \
            f"Original source {original_source_id} should be traceable from final result {final_source_id}"
        
        # Property: Transformation path should exist between original and final
        transformation_path = lineage_service.get_transformation_path(original_source_id, final_source_id)
        assert len(transformation_path) >= 2, "Should have a path from original to final source"
        assert transformation_path[0] == original_source_id, "Path should start with original source"
        assert transformation_path[-1] == final_source_id, "Path should end with final source"
        
        # Property: All intermediate sources should be in the path
        for source_id in source_ids:
            if source_id in [original_source_id, final_source_id]:
                continue  # Skip start and end
            assert source_id in transformation_path, f"Intermediate source {source_id} should be in transformation path"
    
    @given(st.lists(data_source_info(), min_size=1, max_size=10))
    def test_source_registration_traceability(self, source_infos):
        """
        Property: All registered sources should be traceable in the lineage
        """
        lineage_service = self.create_lineage_service()
        registered_ids = []
        
        for source_info in source_infos:
            source_id = lineage_service.register_source(**source_info)
            registered_ids.append(source_id)
        
        # All sources should be in the lineage graph
        for source_id in registered_ids:
            assert source_id in lineage_service.sources, f"Source {source_id} should be registered"
            assert source_id in lineage_service.lineage_graph, f"Source {source_id} should be in lineage graph"
            
            # Should be able to trace each source (even if it has no transformations)
            upstream_lineage = lineage_service.trace_lineage_upstream(source_id)
            assert upstream_lineage["source"]["id"] == source_id, "Source should be traceable to itself"
    
    @given(data_source_info(), data_source_info(), transformation_info())
    def test_transformation_bidirectional_traceability(self, input_source_info, output_source_info, transform_info):
        """
        Property: Transformations should be traceable both upstream and downstream
        """
        lineage_service = self.create_lineage_service()
        # Register sources
        input_id = lineage_service.register_source(**input_source_info)
        output_id = lineage_service.register_source(**output_source_info)
        
        # Record transformation
        transform_id = lineage_service.record_transformation(
            input_source_ids=[input_id],
            output_source_id=output_id,
            **transform_info
        )
        
        # Test upstream tracing from output
        upstream_lineage = lineage_service.trace_lineage_upstream(output_id)
        assert input_id in [upstream["source"]["id"] for upstream in upstream_lineage.get("upstream", {}).values()], \
            "Input source should be traceable upstream from output"
        
        # Test downstream tracing from input
        downstream_lineage = lineage_service.trace_lineage_downstream(input_id)
        assert output_id in [downstream["source"]["id"] for downstream in downstream_lineage.get("downstream", {}).values()], \
            "Output source should be traceable downstream from input"
        
        # Transformation should be recorded in both directions
        assert len(upstream_lineage.get("transformations", [])) > 0, "Output should have transformation recorded"
        
        # Verify transformation details are preserved
        recorded_transform = upstream_lineage["transformations"][0]
        assert recorded_transform["name"] == transform_info["name"], "Transformation name should be preserved"
        assert recorded_transform["type"] == transform_info["transformation_type"].value, "Transformation type should be preserved"
    
    @given(st.lists(data_source_info(), min_size=3, max_size=8))
    def test_complex_lineage_traceability(self, source_infos):
        """
        Property: Complex lineage graphs should maintain traceability
        """
        lineage_service = self.create_lineage_service()
        assume(len(source_infos) >= 3)
        
        # Register all sources
        source_ids = []
        for source_info in source_infos:
            source_id = lineage_service.register_source(**source_info)
            source_ids.append(source_id)
        
        # Create a more complex transformation graph
        # Source 0 -> Source 1, Source 0 -> Source 2, Source 1 + Source 2 -> Source 3 (if exists)
        transformations = []
        
        # Simple transformations
        if len(source_ids) >= 2:
            t1_id = lineage_service.record_transformation(
                name="Transform 1",
                transformation_type=TransformationType.CALCULATION,
                input_source_ids=[source_ids[0]],
                output_source_id=source_ids[1]
            )
            transformations.append(t1_id)
        
        if len(source_ids) >= 3:
            t2_id = lineage_service.record_transformation(
                name="Transform 2",
                transformation_type=TransformationType.ENRICHMENT,
                input_source_ids=[source_ids[0]],
                output_source_id=source_ids[2]
            )
            transformations.append(t2_id)
        
        # Multi-input transformation if we have enough sources
        if len(source_ids) >= 4:
            t3_id = lineage_service.record_transformation(
                name="Merge Transform",
                transformation_type=TransformationType.AGGREGATION,
                input_source_ids=[source_ids[1], source_ids[2]],
                output_source_id=source_ids[3]
            )
            transformations.append(t3_id)
        
        # Property: Original source should be traceable from all derived sources
        original_source_id = source_ids[0]
        
        for i, derived_source_id in enumerate(source_ids[1:], 1):
            upstream_lineage = lineage_service.trace_lineage_upstream(derived_source_id)
            
            def find_source_in_lineage(lineage_data: Dict[str, Any], target_id: str) -> bool:
                if lineage_data.get("source", {}).get("id") == target_id:
                    return True
                for upstream in lineage_data.get("upstream", {}).values():
                    if find_source_in_lineage(upstream, target_id):
                        return True
                return False
            
            assert find_source_in_lineage(upstream_lineage, original_source_id), \
                f"Original source {original_source_id} should be traceable from derived source {derived_source_id}"
    
    @given(st.integers(min_value=1, max_value=20))
    def test_lineage_integrity_validation(self, num_sources):
        """
        Property: Lineage integrity should be maintained and validatable
        """
        lineage_service = self.create_lineage_service()
        # Create valid lineage
        source_ids = []
        for i in range(num_sources):
            source_id = lineage_service.register_source(
                name=f"Source_{i}",
                source_type="test",
                location=f"test://source_{i}"
            )
            source_ids.append(source_id)
        
        # Create some transformations
        for i in range(min(num_sources - 1, 5)):  # Limit transformations to avoid complexity
            lineage_service.record_transformation(
                name=f"Transform_{i}",
                transformation_type=TransformationType.CALCULATION,
                input_source_ids=[source_ids[i]],
                output_source_id=source_ids[i + 1]
            )
        
        # Property: Valid lineage should have no integrity issues
        integrity_issues = lineage_service.validate_lineage_integrity()
        assert len(integrity_issues) == 0, f"Valid lineage should have no integrity issues, but found: {integrity_issues}"
        
        # Property: Lineage summary should be consistent
        summary = lineage_service.get_lineage_summary()
        assert summary["total_sources"] == num_sources, "Summary should report correct number of sources"
        assert len(summary["root_sources"]) >= 1, "Should have at least one root source"
        assert len(summary["leaf_sources"]) >= 1, "Should have at least one leaf source"
    
    @given(data_source_info(), data_source_info())
    def test_empty_transformation_path_handling(self, source1_info, source2_info):
        """
        Property: Unconnected sources should return empty transformation path
        """
        lineage_service = self.create_lineage_service()
        # Register two unconnected sources
        source1_id = lineage_service.register_source(**source1_info)
        source2_id = lineage_service.register_source(**source2_info)
        
        # Property: No transformation path should exist between unconnected sources
        path = lineage_service.get_transformation_path(source1_id, source2_id)
        assert len(path) == 0, "Unconnected sources should have no transformation path"
        
        # Property: Source should have path to itself
        self_path = lineage_service.get_transformation_path(source1_id, source1_id)
        assert self_path == [source1_id], "Source should have path to itself"