"""
Property-based tests for batch processing completeness
Feature: tech-stack-modernization, Property 23: Batch Processing Completeness
"""
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any
from unittest.mock import Mock

from app.services.batch_processing_service import (
    BatchProcessingService,
    BatchJobStatus,
    RecordStatus
)
from app.services.data_quality_service import (
    DataQualityService,
    ValidationSeverity,
    DataQualityLevel,
    DataQualityReport,
    ValidationIssue
)


# Test data generators
@st.composite
def valid_record(draw):
    """Generate a valid data record"""
    return {
        "ticker": draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        "price": draw(st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)),
        "volume": draw(st.integers(min_value=1, max_value=1000000)),
        "timestamp": draw(st.datetimes().map(lambda dt: dt.isoformat()))
    }


@st.composite
def invalid_record(draw):
    """Generate an invalid data record"""
    record_type = draw(st.sampled_from(
        ['missing_ticker', 'negative_price', 'zero_volume', 'invalid_timestamp']))

    if record_type == 'missing_ticker':
        return {
            "price": draw(
                st.floats(
                    min_value=0.01,
                    max_value=10000.0,
                    allow_nan=False,
                    allow_infinity=False)),
            "volume": draw(
                st.integers(
                    min_value=1,
                    max_value=1000000))}
    elif record_type == 'negative_price':
        return {
            "ticker": draw(
                st.text(
                    min_size=1,
                    max_size=10)),
            "price": draw(
                st.floats(
                    max_value=-0.01,
                    allow_nan=False,
                    allow_infinity=False)),
            "volume": draw(
                st.integers(
                    min_value=1,
                    max_value=1000000))}
    elif record_type == 'zero_volume':
        return {
            "ticker": draw(
                st.text(
                    min_size=1,
                    max_size=10)),
            "price": draw(
                st.floats(
                    min_value=0.01,
                    max_value=10000.0,
                    allow_nan=False,
                    allow_infinity=False)),
            "volume": 0}
    else:  # invalid_timestamp
        return {
            "ticker": draw(
                st.text(
                    min_size=1,
                    max_size=10)),
            "price": draw(
                st.floats(
                    min_value=0.01,
                    max_value=10000.0,
                    allow_nan=False,
                    allow_infinity=False)),
            "volume": draw(
                st.integers(
                    min_value=1,
                    max_value=1000000)),
            "timestamp": "invalid-timestamp"}


@st.composite
def mixed_dataset(draw):
    """Generate a dataset with both valid and invalid records"""
    valid_count = draw(st.integers(min_value=1, max_value=50))
    invalid_count = draw(st.integers(min_value=0, max_value=20))

    valid_records = draw(
        st.lists(
            valid_record(),
            min_size=valid_count,
            max_size=valid_count))
    invalid_records = draw(
        st.lists(
            invalid_record(),
            min_size=invalid_count,
            max_size=invalid_count))

    # Shuffle the records
    all_records = valid_records + invalid_records
    draw(st.randoms()).shuffle(all_records)

    return all_records, valid_count, invalid_count


class TestBatchProcessingCompleteness:
    """Test batch processing completeness properties"""

    @pytest.fixture
    def mock_data_quality_service(self):
        """Mock data quality service"""
        service = Mock(spec=DataQualityService)

        async def mock_validate(
                data: Dict[str, Any], data_type: str = "stock_data") -> DataQualityReport:
            # Simple validation logic for testing
            issues = []

            if "ticker" not in data:
                issues.append(ValidationIssue(
                    field="ticker",
                    message="Missing ticker",
                    severity=ValidationSeverity.ERROR,
                    value=None
                ))

            if data.get("price", 0) <= 0:
                issues.append(ValidationIssue(
                    field="price",
                    message="Invalid price",
                    severity=ValidationSeverity.ERROR,
                    value=data.get("price")
                ))

            if data.get("volume", 0) <= 0:
                issues.append(ValidationIssue(
                    field="volume",
                    message="Low volume",
                    severity=ValidationSeverity.WARNING,
                    value=data.get("volume")
                ))

            # Determine overall quality
            error_count = sum(
                1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
            if error_count > 0:
                overall_quality = DataQualityLevel.CRITICAL
            elif issues:
                overall_quality = DataQualityLevel.MEDIUM
            else:
                overall_quality = DataQualityLevel.HIGH

            return DataQualityReport(
                overall_quality=overall_quality,
                quality_score=1.0 - (error_count * 0.5),
                total_fields=len(data),
                valid_fields=len(data) - error_count,
                issues=issues,
                timestamp=datetime.utcnow()
            )

        service.validate_data = mock_validate
        return service

    @pytest.fixture
    def batch_service(self, mock_data_quality_service):
        """Create batch processing service with mocked dependencies"""
        return BatchProcessingService(
            data_quality_service=mock_data_quality_service,
            max_workers=2,
            batch_size=10
        )

    def simple_processor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple processor function for testing"""
        return {
            "processed": True,
            "ticker": data.get("ticker", "UNKNOWN"),
            "calculated_value": data.get("price", 0) * data.get("volume", 0)
        }

    def failing_processor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processor that fails for certain conditions"""
        if data.get("ticker") == "FAIL":
            raise ValueError("Intentional failure")
        return self.simple_processor(data)

    @given(mixed_dataset())
    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_batch_processing_completeness_property(
            self, batch_service, data_tuple):
        """
        Property 23: Batch Processing Completeness
        For any batch job processing a dataset, all valid records should be processed successfully
        and invalid records should be logged with reasons
        **Validates: Requirements 10.4**
        """
        dataset, expected_valid, expected_invalid = data_tuple
        assume(len(dataset) > 0)  # Ensure we have data to process

        # Process the batch
        result = await batch_service.process_batch(
            dataset=dataset,
            processor_func=self.simple_processor,
            validate_input=True
        )

        # Property assertions
        assert result.status == BatchJobStatus.COMPLETED, "Batch job should complete successfully"
        assert result.total_records == len(
            dataset), "Total records should match input dataset size"

        # All records should be processed (either successfully or with logged failures)
        processed_count = result.successful_records + \
            result.failed_records + result.skipped_records
        assert processed_count == result.total_records, "All records should be processed"

        # All failed records should have error messages logged
        failed_records = [r for r in result.records if r.status == RecordStatus.FAILED]
        assert len(
            failed_records) == result.failed_records, "Failed record count should match"

        for record in failed_records:
            assert record.error_message is not None, f"Failed record {
                record.id} should have error message"
            assert record.processed_at is not None, f"Failed record {
                record.id} should have processed timestamp"

        # All successful records should have results
        successful_records = [
            r for r in result.records if r.status == RecordStatus.SUCCESS]
        assert len(
            successful_records) == result.successful_records, "Successful record count should match"

        for record in successful_records:
            assert record.result is not None, f"Successful record {
                record.id} should have result"
            assert record.processed_at is not None, f"Successful record {
                record.id} should have processed timestamp"
            assert "processed" in record.result, "Result should contain processed flag"

        # Error summary should contain all error messages
        if result.failed_records > 0:
            assert len(
                result.error_summary) > 0, "Error summary should contain error messages for failed records"

            # Each failed record should have corresponding error in summary
            failed_record_ids = {r.id for r in failed_records}
            summary_record_ids = {
                line.split(":")[0].replace("Record ", "")
                for line in result.error_summary
                if line.startswith("Record ")
            }
            assert failed_record_ids.issubset(
                summary_record_ids), "All failed records should be in error summary"

    @given(st.lists(valid_record(), min_size=1, max_size=20))
    @pytest.mark.asyncio
    async def test_all_valid_records_processed_successfully(
            self, batch_service, valid_dataset):
        """
        Property: All valid records in a batch should be processed successfully
        """
        result = await batch_service.process_batch(
            dataset=valid_dataset,
            processor_func=self.simple_processor,
            validate_input=True
        )

        assert result.status == BatchJobStatus.COMPLETED
        assert result.successful_records == len(valid_dataset)
        assert result.failed_records == 0
        assert result.success_rate == 100.0

        # All records should have results
        for record in result.records:
            assert record.status == RecordStatus.SUCCESS
            assert record.result is not None
            assert record.error_message is None

    @given(st.lists(invalid_record(), min_size=1, max_size=20))
    @pytest.mark.asyncio
    async def test_all_invalid_records_logged_with_reasons(
            self, batch_service, invalid_dataset):
        """
        Property: All invalid records should be logged with specific error reasons
        """
        result = await batch_service.process_batch(
            dataset=invalid_dataset,
            processor_func=self.simple_processor,
            validate_input=True
        )

        assert result.status == BatchJobStatus.COMPLETED
        assert result.failed_records > 0  # Should have some failures due to validation

        # All failed records should have specific error messages
        failed_records = [r for r in result.records if r.status == RecordStatus.FAILED]
        for record in failed_records:
            assert record.error_message is not None
            assert len(record.error_message.strip()) > 0
            assert "Validation" in record.error_message or "error" in record.error_message.lower()

    @given(st.lists(valid_record(), min_size=5, max_size=20))
    @pytest.mark.asyncio
    async def test_processor_failures_are_logged(self, batch_service, dataset):
        """
        Property: When processor function fails, the failure should be logged with reason
        """
        # Add some records that will cause processor to fail
        failing_records = [{"ticker": "FAIL", "price": 100.0, "volume": 1000}]
        mixed_dataset = dataset + failing_records

        result = await batch_service.process_batch(
            dataset=mixed_dataset,
            processor_func=self.failing_processor,
            validate_input=True
        )

        assert result.status == BatchJobStatus.COMPLETED
        assert result.failed_records >= len(failing_records)

        # Check that processor failures are logged
        processor_failed_records = [
            r for r in result.records if r.status == RecordStatus.FAILED and "Processing error" in (
                r.error_message or "")]
        assert len(processor_failed_records) >= len(failing_records)

        for record in processor_failed_records:
            assert "Processing error" in record.error_message
            assert record.processed_at is not None

    @given(st.integers(min_value=1, max_value=100))
    @pytest.mark.asyncio
    async def test_empty_dataset_handling(self, batch_service, _):
        """
        Property: Empty datasets should be handled gracefully
        """
        result = await batch_service.process_batch(
            dataset=[],
            processor_func=self.simple_processor,
            validate_input=True
        )

        assert result.status == BatchJobStatus.COMPLETED
        assert result.total_records == 0
        assert result.successful_records == 0
        assert result.failed_records == 0
        assert result.success_rate == 0.0
        assert len(result.records) == 0
        assert len(result.error_summary) == 0

    @given(st.lists(valid_record(), min_size=1, max_size=50))
    @pytest.mark.asyncio
    async def test_batch_job_metadata_completeness(self, batch_service, dataset):
        """
        Property: Batch job results should contain complete metadata
        """
        result = await batch_service.process_batch(
            dataset=dataset,
            processor_func=self.simple_processor,
            validate_input=True
        )

        # Metadata completeness checks
        assert result.job_id is not None and len(result.job_id) > 0
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at
        assert result.total_records == len(dataset)
        assert isinstance(result.success_rate, float)
        assert 0.0 <= result.success_rate <= 100.0

        # Record-level metadata
        for record in result.records:
            assert record.id is not None and len(record.id) > 0
            assert record.processed_at is not None
            assert record.status in [
                RecordStatus.SUCCESS,
                RecordStatus.FAILED,
                RecordStatus.SKIPPED]
