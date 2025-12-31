"""Performance tests comparing convert_with_ai vs pure docling."""

import time

import pytest

from opendataloader_pdf.hybrid import HybridPipeline, HybridPipelineConfig


@pytest.fixture(scope="module")
def perf_output_dir(module_output_dir):
    """Create performance test output directory."""
    perf_dir = module_output_dir / "perf"
    perf_dir.mkdir(exist_ok=True)
    return perf_dir


class TestPerformance:
    """Performance comparison tests."""

    def test_profile_convert_with_ai(self, input_pdf, perf_output_dir):
        """Profile convert_with_ai to identify bottlenecks using built-in metrics."""
        from docling.document_converter import DocumentConverter

        hybrid_dir = perf_output_dir / "profile"
        hybrid_dir.mkdir(exist_ok=True)

        # Run hybrid pipeline with metrics
        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        pipeline.process(str(input_pdf), str(hybrid_dir))

        # Get metrics from pipeline
        metrics = pipeline.metrics
        assert metrics is not None, "Pipeline should have metrics"

        # Compare with pure docling on full PDF
        docling_start = time.perf_counter()
        converter = DocumentConverter()
        converter.convert(str(input_pdf))
        docling_time = time.perf_counter() - docling_start

        # Print comparison
        print(metrics.summary())
        print("\nComparison with pure docling:")
        print("=" * 70)
        print(f"Pure docling (full):    {docling_time:6.2f}s")
        print(f"Hybrid total:           {metrics.total_duration:6.2f}s")
        speedup = docling_time / metrics.total_duration if metrics.total_duration > 0 else 0
        print(f"Speedup:                {speedup:.2f}x")
        print("=" * 70)

        # Performance assertions based on AI ratio
        if metrics.ai_ratio < 0.3:
            assert metrics.total_duration < docling_time * 1.1, (
                f"Hybrid ({metrics.total_duration:.2f}s) should be faster "
                f"than docling ({docling_time:.2f}s) when AI ratio is low"
            )
        else:
            print(f"Note: High AI ratio ({metrics.ai_ratio:.0%}) - hybrid optimization limited")

        # Verify metrics are populated
        assert metrics.jar_phase.duration > 0, "JAR phase should have duration"
        assert metrics.ai_phase.duration > 0, "AI phase should have duration"
        assert metrics.merge_phase.duration > 0, "Merge phase should have duration"

    def test_metrics_dict_export(self, input_pdf, perf_output_dir):
        """Test that metrics can be exported to dict for JSON serialization."""
        hybrid_dir = perf_output_dir / "metrics_export"
        hybrid_dir.mkdir(exist_ok=True)

        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        pipeline.process(str(input_pdf), str(hybrid_dir))

        metrics = pipeline.metrics
        metrics_dict = metrics.to_dict()

        # Verify dict structure
        assert "total_duration" in metrics_dict
        assert "phases" in metrics_dict
        assert "jar" in metrics_dict["phases"]
        assert "ai" in metrics_dict["phases"]
        assert "merge" in metrics_dict["phases"]
        assert "seconds_per_page" in metrics_dict["phases"]["ai"]

        print("\nMetrics JSON export:")
        import json
        print(json.dumps(metrics_dict, indent=2))
