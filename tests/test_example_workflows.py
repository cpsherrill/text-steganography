"""Run the documented workflows so examples cannot silently drift from the API."""
from pathlib import Path
import runpy

import pytest


@pytest.mark.parametrize('filename', [
    'recipient_fingerprints.py', 'transport_probe.py', 'source_comments.py',
])
def test_example_workflow(filename, capsys):
    path = Path(__file__).resolve().parents[1] / 'examples' / filename
    runpy.run_path(str(path), run_name='__main__')
    assert capsys.readouterr().out
