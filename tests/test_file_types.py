import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from codebased.parsers.file_types import get_file_type


def test_get_file_type_mappings():
    assert get_file_type('main.py') == 'python'
    assert get_file_type('script.js') == 'javascript'
    assert get_file_type('styles.css') == 'css'
    assert get_file_type('index.html') == 'html'
    assert get_file_type('data.json') == 'json'


def test_get_file_type_patterns():
    assert get_file_type('app.component.ts') == 'angular'
    assert get_file_type('app.module.ts') == 'angular'
    assert get_file_type('auth.service.ts') == 'angular'
    assert get_file_type('foo.component.html') == 'angular'
    assert get_file_type('foo.component.css') == 'angular'
    # generic ts should still be typescript
    assert get_file_type('foo.ts') == 'typescript'
