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

    @pytest.mark.skip(reason="Benchmark test - run manually")
    def test_individual_vs_range_pages(self, input_pdf, warmed_converter):
        """Compare individual page calls vs range call for sparse AI pages.

        Tests whether calling docling once per AI page is faster than
        calling once with a range that includes non-AI pages.

        Sample result (2024-12-31, M3 MacBook Pro):
        ----------------------------------------------------------------------
        AI pages: [1, 2, 3, 4, 5, 7, 9, 10, 12] (9 pages)
        Range would process: 1-12 (12 pages)
        ----------------------------------------------------------------------
        Individual pages (9 calls): 8.50s
        Range 1-12 (1 call):        10.16s
        Full PDF (15 pages):        10.64s
        ----------------------------------------------------------------------
        Individual vs Range: -1.67s
        Individual vs Full:  -2.14s
        ======================================================================
        Individual page calls are FASTER
        """
        from docling.document_converter import DocumentConverter

        # Warm up models
        warmed_converter.convert(str(input_pdf), page_range=(1, 1))

        # Simulate 9 AI pages spread in 1-12 range (like real triage result)
        ai_pages = [1, 2, 3, 4, 5, 7, 9, 10, 12]

        print("\n" + "=" * 70)
        print("Individual pages vs Range comparison")
        print("=" * 70)
        print(f"AI pages: {ai_pages} ({len(ai_pages)} pages)")
        print("Range would process: 1-12 (12 pages)")
        print("-" * 70)

        # Test 1: Individual page calls (reusing converter)
        converter1 = DocumentConverter()
        start = time.perf_counter()
        for p in ai_pages:
            converter1.convert(str(input_pdf), page_range=(p, p))
        individual_time = time.perf_counter() - start
        print(f"Individual pages ({len(ai_pages)} calls): {individual_time:.2f}s")

        # Test 2: Range 1-12 (single call)
        converter2 = DocumentConverter()
        start = time.perf_counter()
        converter2.convert(str(input_pdf), page_range=(1, 12))
        range_time = time.perf_counter() - start
        print(f"Range 1-12 (1 call):            {range_time:.2f}s")

        # Test 3: Full PDF for reference
        converter3 = DocumentConverter()
        start = time.perf_counter()
        converter3.convert(str(input_pdf))
        full_time = time.perf_counter() - start
        print(f"Full PDF (15 pages):            {full_time:.2f}s")

        print("-" * 70)
        print(f"Individual vs Range: {individual_time - range_time:+.2f}s")
        print(f"Individual vs Full:  {individual_time - full_time:+.2f}s")
        print("=" * 70)

        if individual_time < range_time:
            print("✓ Individual page calls are FASTER")
        else:
            print("✗ Range call is faster")

    @pytest.mark.skip(reason="Benchmark test - run manually")
    def test_docling_conversion_consistency(self, input_pdf, warmed_converter):
        """Test docling conversion time consistency across multiple runs.

        Verifies that:
        1. First call has model loading overhead
        2. Subsequent calls with same converter are faster
        3. New converter instances share loaded models

        Sample result (2024-12-31, M3 MacBook Pro):
        ======================================================================
        Docling conversion time consistency test
        ======================================================================

        Same converter instance (3 runs):
        ----------------------------------------------------------------------
          Run 1: 11.71s
          Run 2: 9.67s
          Run 3: 9.14s
          Avg: 10.17s, Diff: 2.57s

        New converter instance each run:
        ----------------------------------------------------------------------
          Run 1: 10.12s
          Run 2: 10.49s
          Run 3: 10.14s
          Avg: 10.25s, Diff: 0.38s
        ======================================================================
        """
        from docling.document_converter import DocumentConverter

        # Warm up models first
        warmed_converter.convert(str(input_pdf), page_range=(1, 1))

        print("\n" + "=" * 70)
        print("Docling conversion time consistency test")
        print("=" * 70)

        # Test with same converter instance
        print("\nSame converter instance (3 runs):")
        print("-" * 70)
        converter = DocumentConverter()
        same_instance_times = []
        for i in range(3):
            start = time.perf_counter()
            converter.convert(str(input_pdf))
            elapsed = time.perf_counter() - start
            same_instance_times.append(elapsed)
            print(f"  Run {i + 1}: {elapsed:.2f}s")
        avg = sum(same_instance_times) / len(same_instance_times)
        diff = max(same_instance_times) - min(same_instance_times)
        print(f"  Avg: {avg:.2f}s, Diff: {diff:.2f}s")

        # Test with new converter instance each time
        print("\nNew converter instance each run:")
        print("-" * 70)
        new_instance_times = []
        for i in range(3):
            conv = DocumentConverter()
            start = time.perf_counter()
            conv.convert(str(input_pdf))
            elapsed = time.perf_counter() - start
            new_instance_times.append(elapsed)
            print(f"  Run {i + 1}: {elapsed:.2f}s")
        avg = sum(new_instance_times) / len(new_instance_times)
        diff = max(new_instance_times) - min(new_instance_times)
        print(f"  Avg: {avg:.2f}s, Diff: {diff:.2f}s")

        print("=" * 70)

        # First run with same instance should be slower (model loading)
        assert same_instance_times[0] > same_instance_times[2], (
            "First run should be slower due to model loading"
        )

    @pytest.mark.skip(reason="Benchmark test - run manually")
    def test_docling_page_range_scaling(self, input_pdf):
        """Test how docling performance scales with different page ranges.

        Includes full initialization time for realistic comparison.

        Sample result (2024-12-31, M3 MacBook Pro):
        ======================================================================
        Docling page_range scaling test
        ======================================================================
        Range           Pages            Time     Per Page    Speedup
        ----------------------------------------------------------------------
        1-1             1               2.48s        2.48s      4.16x
        1-3             3               1.92s        0.64s      5.39x
        1-7             7               3.91s        0.56s      2.64x
        1-12            12              9.36s        0.78s      1.10x
        1-15            15             10.31s        0.69s      1.00x
        ======================================================================
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
