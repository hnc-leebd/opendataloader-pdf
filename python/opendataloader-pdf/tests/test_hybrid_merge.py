"""Tests for result merger."""

import json
import tempfile
from pathlib import Path

import pytest

from opendataloader_pdf.hybrid.merge import ResultMerger


class TestResultMerger:
    """Tests for ResultMerger class."""

    @pytest.fixture
    def work_dir(self):
        """Create a temporary working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_load_triage_file_exists(self, work_dir):
        """Test loading triage.json when it exists."""
        triage_data = {
            "pages": [
                {"page": 1, "path": "fast"},
                {"page": 2, "path": "ai", "needs_ocr": True},
            ]
        }
        (work_dir / "triage.json").write_text(json.dumps(triage_data))

        merger = ResultMerger(work_dir)
        result = merger.load_triage()

        assert len(result["pages"]) == 2
        assert result["pages"][0]["path"] == "fast"
        assert result["pages"][1]["path"] == "ai"

    def test_load_triage_file_not_exists(self, work_dir):
        """Test loading triage.json when it doesn't exist."""
        merger = ResultMerger(work_dir)
        result = merger.load_triage()

        assert result == {"pages": []}

    def test_load_fast_pages_file_exists(self, work_dir):
        """Test loading fast_pages.json when it exists."""
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 2,
            "author": "Test Author",
            "title": "Test Title",
            "creation date": None,
            "modification date": None,
            "kids": [
                {"type": "paragraph", "page number": 1, "content": "Page 1 text"}
            ],
        }
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        merger = ResultMerger(work_dir)
        result = merger.load_fast_results()

        assert result["file name"] == "test.pdf"
        assert len(result["kids"]) == 1

    def test_load_fast_pages_file_not_exists(self, work_dir):
        """Test loading fast_pages.json when it doesn't exist."""
        merger = ResultMerger(work_dir)
        result = merger.load_fast_results()

        assert result == {"kids": []}

    def test_merge_fast_only(self, work_dir):
        """Test merge with only fast-path pages."""
        triage_data = {
            "pages": [
                {"page": 1, "path": "fast"},
                {"page": 2, "path": "fast"},
            ]
        }
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 2,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [
                {"type": "paragraph", "page number": 1, "bounding box": [0, 0, 100, 20], "content": "Page 1"},
                {"type": "paragraph", "page number": 2, "bounding box": [0, 0, 100, 20], "content": "Page 2"},
            ],
        }
        (work_dir / "triage.json").write_text(json.dumps(triage_data))
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        merger = ResultMerger(work_dir)
        result = merger.merge({})

        assert result["file name"] == "test.pdf"
        assert result["number of pages"] == 2
        assert len(result["kids"]) == 2

    def test_merge_ai_only(self, work_dir):
        """Test merge with only AI-path pages."""
        triage_data = {
            "pages": [
                {"page": 1, "path": "ai", "needs_ocr": True},
            ]
        }
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 1,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [],
        }
        (work_dir / "triage.json").write_text(json.dumps(triage_data))
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        ai_results = {
            0: {  # 0-indexed
                "elements": [
                    {"type": "paragraph", "bounding box": [0, 0, 100, 20], "content": "OCR text"},
                ],
            }
        }

        merger = ResultMerger(work_dir)
        result = merger.merge(ai_results)

        assert len(result["kids"]) == 1
        assert result["kids"][0]["content"] == "OCR text"
        assert result["kids"][0]["page number"] == 1

    def test_merge_mixed_paths(self, work_dir):
        """Test merge with mixed fast and AI paths."""
        triage_data = {
            "pages": [
                {"page": 1, "path": "fast"},
                {"page": 2, "path": "ai", "needs_ocr": True},
                {"page": 3, "path": "fast"},
            ]
        }
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 3,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [
                {"type": "paragraph", "page number": 1, "bounding box": [0, 0, 100, 20], "content": "Fast page 1"},
                {"type": "paragraph", "page number": 3, "bounding box": [0, 0, 100, 20], "content": "Fast page 3"},
            ],
        }
        (work_dir / "triage.json").write_text(json.dumps(triage_data))
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        ai_results = {
            1: {  # Page 2 (0-indexed)
                "elements": [
                    {"type": "paragraph", "bounding box": [0, 0, 100, 20], "content": "AI page 2"},
                ],
            }
        }

        merger = ResultMerger(work_dir)
        result = merger.merge(ai_results)

        assert len(result["kids"]) == 3
        # Check order is maintained
        assert result["kids"][0]["page number"] == 1
        assert result["kids"][1]["page number"] == 2
        assert result["kids"][2]["page number"] == 3

    def test_sort_elements_by_position(self, work_dir):
        """Test that elements are sorted by page and position."""
        triage_data = {"pages": [{"page": 1, "path": "fast"}]}
        fast_data = {
            "file name": "test.pdf",
            "number of pages": 1,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [
                {"type": "paragraph", "page number": 1, "bounding box": [0, 100, 100, 120], "content": "Bottom"},
                {"type": "paragraph", "page number": 1, "bounding box": [0, 0, 100, 20], "content": "Top"},
            ],
        }
        (work_dir / "triage.json").write_text(json.dumps(triage_data))
        (work_dir / "fast_pages.json").write_text(json.dumps(fast_data))

        merger = ResultMerger(work_dir)
        result = merger.merge({})

        # Should be sorted by y position (top to bottom)
        assert result["kids"][0]["content"] == "Top"
        assert result["kids"][1]["content"] == "Bottom"

    def test_write_output(self, work_dir):
        """Test writing merged result to file."""
        result = {
            "file name": "test.pdf",
            "number of pages": 1,
            "author": None,
            "title": None,
            "creation date": None,
            "modification date": None,
            "kids": [{"type": "paragraph", "content": "Test"}],
        }
        output_path = work_dir / "output.json"

        merger = ResultMerger(work_dir)
        merger.write_output(result, output_path)

        assert output_path.exists()
        loaded = json.loads(output_path.read_text())
        assert loaded["file name"] == "test.pdf"
