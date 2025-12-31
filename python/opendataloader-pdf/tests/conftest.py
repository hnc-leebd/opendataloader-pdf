import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def input_pdf():
    return Path(__file__).resolve().parents[3] / "samples" / "pdf" / "1901.03003.pdf"


@pytest.fixture
def output_dir():
    path = (
        Path(__file__).resolve().parents[3]
        / "python"
        / "opendataloader-pdf"
        / "tests"
        / "temp"
    )
    path.mkdir(exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def module_output_dir():
    """Module-scoped output directory for shared test results."""
    path = (
        Path(__file__).resolve().parents[3]
        / "python"
        / "opendataloader-pdf"
        / "tests"
        / "temp_module"
    )
    path.mkdir(exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)
