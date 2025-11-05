import re

from reporting.markdown_generator import MarkdownReportGenerator


def test_youtube_title_from_channel():
    gen = MarkdownReportGenerator()
    report_data = {
        'appendix': [
            {
                'content_id': 'video1',
                'meta': {
                    'source_url': 'https://www.youtube.com/watch?v=AbCdEf1',
                    'channel_title': 'TestChannel',
                },
                'final_score': 35.0,
                'label': 'inauthentic',
            }
        ]
    }

    out = gen._create_appendix(report_data)
    # Expect the YouTube channel-based title
    assert 'YouTube: TestChannel' in out
    # And the visited URL should include the youtube watch URL
    assert 'https://www.youtube.com/watch?v=AbCdEf1' in out


def test_youtube_title_from_video_id():
    gen = MarkdownReportGenerator()
    report_data = {
        'appendix': [
            {
                'content_id': 'youtube_video_XYZ1234',
                'meta': {
                    'source_url': '',
                },
                'final_score': 20.0,
                'label': 'inauthentic',
            }
        ]
    }

    out = gen._create_appendix(report_data)
    # Expect fallback title constructed from content_id
    assert re.search(r'YouTube video\s+XYZ1234', out)
    # Expect constructed watch URL
    assert 'https://www.youtube.com/watch?v=XYZ1234' in out
