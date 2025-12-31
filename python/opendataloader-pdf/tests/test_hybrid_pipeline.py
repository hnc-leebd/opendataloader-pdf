"""Tests for hybrid pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from opendataloader_pdf.hybrid import HybridPipeline, HybridPipelineConfig


class TestHybridPipeline:
    """Tests for HybridPipeline class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return HybridPipelineConfig()

    @pytest.fixture
    def work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_with_default_config(self):
        """Test pipeline initialization with default config."""
        pipeline = HybridPipeline()
        assert pipeline.config is not None
        assert pipeline.config.batch_size == 4

    def test_init_with_custom_config(self, config):
        """Test pipeline initialization with custom config."""
        config.batch_size = 8
        pipeline = HybridPipeline(config)
        assert pipeline.config.batch_size == 8

    def test_process_file_not_found(self, config):
        """Test process raises error for missing file."""
        pipeline = HybridPipeline(config)

        with pytest.raises(FileNotFoundError):
            pipeline.process("nonexistent.pdf")

    @patch("opendataloader_pdf.hybrid.pipeline.run_jar")
    def test_process_runs_jar_with_hybrid_flag(self, mock_run_jar, work_dir):
        """Test that process calls JAR with --hybrid flag."""
        # Create a mock PDF file
        pdf_path = work_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")

        # Create triage.json (all fast path)
        triage_data = {"pages": [{"page": 1, "path": "fast"}]}
        (work_dir / "triage.json").write_text(json.dumps(triage_data))

        # Create fast_pages.json
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 1,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [],
        }
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        pipeline.process(pdf_path, work_dir)

        # Verify run_jar was called with --hybrid
        mock_run_jar.assert_called_once()
        args = mock_run_jar.call_args[0][0]
        assert "--hybrid" in args

    @patch("opendataloader_pdf.hybrid.pipeline.run_jar")
    def test_process_handles_password(self, mock_run_jar, work_dir):
        """Test that process passes password to JAR."""
        pdf_path = work_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")

        triage_data = {"pages": []}
        (work_dir / "triage.json").write_text(json.dumps(triage_data))
        fast_data = {"file name": "test.pdf", "number of pages": 0, "author": None, "title": None, "creation date": None, "modification date": None, "kids": []}
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        pipeline.process(pdf_path, work_dir, password="secret")

        args = mock_run_jar.call_args[0][0]
        assert "--password" in args
        assert "secret" in args

    @patch("opendataloader_pdf.hybrid.pipeline.run_jar")
    def test_process_returns_merged_result(self, mock_run_jar, work_dir):
        """Test that process returns merged JSON result."""
        pdf_path = work_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")

        triage_data = {"pages": [{"page": 1, "path": "fast"}]}
        (work_dir / "triage.json").write_text(json.dumps(triage_data))

        fast_data = {
            "file name": "test.pdf",
            "number of pages": 1,
            "author": "Test Author",
            "title": "Test Title",
            "creation date": None,
            "modification date": None,
            "kids": [
                {"type": "paragraph", "page number": 1, "bounding box": [0, 0, 100, 20], "content": "Test content"}
            ],
        }
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        config = HybridPipelineConfig(keep_intermediate=True)
        pipeline = HybridPipeline(config)
        result = pipeline.process(pdf_path, work_dir)

        assert result["file name"] == "test.pdf"
        assert result["number of pages"] == 1
        assert len(result["kids"]) == 1
        assert result["kids"][0]["content"] == "Test content"

    def test_get_ai_pages(self):
        """Test extracting AI pages from triage data."""
        pipeline = HybridPipeline()

        triage = {
            "pages": [
                {"page": 1, "path": "fast"},
                {"page": 2, "path": "ai", "needs_ocr": True},
                {"page": 3, "path": "fast"},
                {"page": 4, "path": "ai", "needs_table_ai": True},
            ]
        }

        ai_pages = pipeline._get_ai_pages(triage)

        assert len(ai_pages) == 2
        assert ai_pages[0]["page"] == 2
        assert ai_pages[1]["page"] == 4

    def test_setup_work_dir_creates_directory(self):
        """Test work directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            pipeline = HybridPipeline()

            work_dir = pipeline._setup_work_dir(output_dir)

            assert work_dir.exists()
            assert work_dir == output_dir

    def test_setup_work_dir_uses_temp_when_none(self):
        """Test temp directory is used when output_dir is None."""
        config = HybridPipelineConfig()
        pipeline = HybridPipeline(config)

        work_dir = pipeline._setup_work_dir(None)

        assert work_dir.exists()
        assert "hybrid_" in str(work_dir)

        # Cleanup
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


class TestHybridPipelineIntegration:
    """Integration tests for HybridPipeline (require JAR and PDF)."""

    @pytest.fixture
    def input_pdf(self):
        """Get path to test PDF."""
        pdf_path = Path(__file__).resolve().parents[3] / "samples" / "pdf" / "1901.03003.pdf"
        if not pdf_path.exists():
            pytest.skip("Test PDF not found")
        return pdf_path

    @pytest.mark.skip(reason="Requires JAR build and AI dependencies")
    def test_full_pipeline_with_real_pdf(self, input_pdf):
        """Test full pipeline with real PDF (skipped by default)."""
        config = HybridPipelineConfig.fast_mode()
        pipeline = HybridPipeline(config)

        result = pipeline.process(input_pdf)

        assert "file name" in result
        assert "number of pages" in result
        assert "kids" in result
