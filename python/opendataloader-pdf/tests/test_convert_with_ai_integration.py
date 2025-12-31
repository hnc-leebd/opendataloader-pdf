"""Integration tests for convert_with_ai (slow, requires docling)."""

import json

import pytest

import opendataloader_pdf
from opendataloader_pdf.hybrid import HybridPipelineConfig


@pytest.fixture(scope="module")
def hybrid_result(input_pdf, module_output_dir):
    """Run convert_with_ai once and share result across tests."""
    hybrid_dir = module_output_dir / "hybrid"
    hybrid_dir.mkdir(exist_ok=True)

    config = HybridPipelineConfig(keep_intermediate=True)
    result = opendataloader_pdf.convert_with_ai(
        input_path=str(input_pdf),
        output_dir=str(hybrid_dir),
        config=config,
    )
    return {"result": result, "output_dir": hybrid_dir}


class TestConvertWithAiIntegration:
    """Integration tests for convert_with_ai function."""

    def test_returns_valid_dict(self, hybrid_result):
        """Verify convert_with_ai returns a valid dictionary with required fields."""
        result = hybrid_result["result"]

        assert isinstance(result, dict)
        assert "number of pages" in result
        assert "kids" in result
        assert result["number of pages"] > 0
        assert len(result["kids"]) > 0

    def test_generates_output_files(self, hybrid_result):
        """Verify all expected output files are generated."""
        output_dir = hybrid_result["output_dir"]

        # Main JSON output
        json_output = output_dir / "1901.03003.json"
        assert json_output.exists(), f"JSON output not found at {json_output}"
        assert json_output.stat().st_size > 0

        # Triage JSON
        triage_output = output_dir / "triage.json"
        assert triage_output.exists()
        with open(triage_output) as f:
            triage = json.load(f)
        assert "pages" in triage
        for page in triage["pages"]:
            assert page["path"] in ("fast", "ai")

        # Fast pages JSON
        fast_pages_output = output_dir / "fast_pages.json"
        assert fast_pages_output.exists()

        # AI page images (if any AI pages)
        ai_pages_dir = output_dir / "ai_pages"
        if ai_pages_dir.exists():
            png_files = list(ai_pages_dir.glob("*.png"))
            assert all(f.name.startswith("page_") for f in png_files)

    def test_extracts_content_from_all_pages(self, hybrid_result):
        """Verify content extraction coverage across pages."""
        result = hybrid_result["result"]
        num_pages = result["number of pages"]

        pages_with_content = {kid.get("page number") for kid in result["kids"] if kid.get("page number")}

        assert len(pages_with_content) >= num_pages * 0.8, (
            f"Expected 80%+ page coverage, got {len(pages_with_content)}/{num_pages}"
        )

    def test_json_schema_compliance(self, hybrid_result):
        """Verify output conforms to OpenDataLoader JSON schema."""
        result = hybrid_result["result"]

        # Root fields
        assert "file name" in result or "file_name" in result
        assert "number of pages" in result or "number_of_pages" in result
        assert "kids" in result

        # Element structure
        for kid in result["kids"][:10]:
            assert "type" in kid
            assert "page number" in kid or "page_number" in kid

            if kid.get("type") in ("paragraph", "heading", "caption", "list item"):
                assert "content" in kid
