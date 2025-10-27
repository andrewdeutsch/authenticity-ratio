import os
from types import SimpleNamespace

import pytest


def test_programmatic_quick_run_monkeypatched(tmp_path, monkeypatch):
    """Ensure programmatic_quick_run returns the expected shape and uses run_pipeline_for_contents."""
    # Arrange: create a fake result and monkeypatch the run_pipeline helper
    fake_result = {
        'run_id': '20251015_000000',
        'pdf': str(tmp_path / 'ar_report_brand_20251015_000000.pdf'),
        'md': str(tmp_path / 'ar_report_brand_20251015_000000.md'),
        'items': 3
    }

    def fake_run_pipeline_for_contents(urls, output_dir='./output', brand_id='brand', sources=None, keywords=None, include_comments=None):
        # write the files to simulate generator behavior
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'dummy.pdf'), 'wb') as f:
            f.write(b'%PDF-1.4')
        with open(os.path.join(output_dir, 'dummy.md'), 'w', encoding='utf-8') as f:
            f.write('# Dummy')
        return fake_result

    monkeypatch.setattr('scripts.run_pipeline.run_pipeline_for_contents', fake_run_pipeline_for_contents)

    # Act: import the app and call programmatic_quick_run
    from webapp import app

    urls = ['https://example.com/1', 'https://example.com/2', 'https://example.com/3']
    outdir = str(tmp_path / 'out')
    res = app.programmatic_quick_run(urls, output_dir=outdir, brand_id='brand')

    # Assert
    assert isinstance(res, dict)
    assert res['run_id'] == fake_result['run_id']
    assert res['items'] == fake_result['items']
    assert os.path.exists(outdir)
