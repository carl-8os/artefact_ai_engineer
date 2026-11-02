"""Regression checks for the responsive static interface."""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'src' / 'music_store' / 'presentation' / 'web_static'


def test_mobile_layout_wraps_suggestions_and_keeps_chat_scrollable():
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    assert '.suggestions {' in css
    assert 'flex-wrap: wrap;' in css
    assert 'height: 100dvh;' in css
    assert 'overflow-y: auto;' in css
    assert 'min-width: 0;' in css
    assert '@media (max-width: 359px)' in css


def test_accessible_mobile_viewport_and_english_ui():
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert '<html lang="en">' in html
    assert 'name="viewport"' in html
    assert 'Emporio Music Store' in html
