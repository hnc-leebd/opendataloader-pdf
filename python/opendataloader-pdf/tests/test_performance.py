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


@pytest.fixture(scope="module")
def warmed_converter():
    """Create a warmed-up DocumentConverter for fair comparison.

    Docling models have significant initialization overhead on first use.
    This fixture ensures all comparisons use an already-initialized converter.
    """
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    return converter


class TestPerformance:
    """Performance comparison tests."""

    def test_profile_convert_with_ai(self, input_pdf, perf_output_dir, warmed_converter):
        """Profile convert_with_ai to identify bottlenecks using built-in metrics."""
        from docling.document_converter import DocumentConverter

        hybrid_dir = perf_output_dir / "profile"
        hybrid_dir.mkdir(exist_ok=True)

        # Warm up docling models globally (affects all DocumentConverter instances)
        warmed_converter.convert(str(input_pdf), page_range=(1, 1))

        # Run pure docling with NEW converter (same as hybrid does internally)
        docling_start = time.perf_counter()
        fresh_converter = DocumentConverter()
        fresh_converter.convert(str(input_pdf))
        docling_time = time.perf_counter() - docling_start

        # Run hybrid pipeline with metrics (also creates new converter internally)
        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        pipeline.process(str(input_pdf), str(hybrid_dir))

        # Get metrics from pipeline
        metrics = pipeline.metrics
        assert metrics is not None, "Pipeline should have metrics"

        # Print comparison
        print(metrics.summary())
        print("\nComparison with pure docling (fresh converter):")
        print("=" * 70)
        print(f"Pure docling (full):    {docling_time:6.2f}s")
        print(f"Hybrid AI phase:        {metrics.ai_phase.duration:6.2f}s")
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

    @pytest.mark.skip(reason="Benchmark test - run manually with pytest -k page_range")
    def test_docling_page_range_scaling(self, input_pdf):
        """Test how docling performance scales with different page ranges.

        Includes full initialization time for realistic comparison.
        """
        from docling.document_converter import DocumentConverter

        # Test PDF is 15 pages
        ranges = [(1, 1), (1, 3), (1, 7), (1, 12), (1, 15)]

        print("\n" + "=" * 70)
        print("Docling page_range scaling test")
        print("=" * 70)
        print(f"{'Range':<15} {'Pages':<10} {'Time':>10} {'Per Page':>12} {'Speedup':>10}")
        print("-" * 70)

        results = []
        for start, end in ranges:
            converter = DocumentConverter()
            start_time = time.perf_counter()
            converter.convert(str(input_pdf), page_range=(start, end))
            elapsed = time.perf_counter() - start_time

            pages = end - start + 1
            per_page = elapsed / pages
            results.append((start, end, pages, elapsed, per_page))

        # Calculate speedup relative to full PDF
        full_time = results[-1][3]
        for start, end, pages, elapsed, per_page in results:
            speedup = full_time / elapsed if elapsed > 0 else 0
            print(f"{start}-{end:<13} {pages:<10} {elapsed:>9.2f}s {per_page:>11.2f}s {speedup:>9.2f}x")

        print("=" * 70)

        # Verify that fewer pages is faster (with some tolerance for variance)
        assert results[0][3] < results[-1][3], "Single page should be faster than full PDF"

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
