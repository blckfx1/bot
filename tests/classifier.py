import pytest
from classifier.engine import Classifier
from db.models import Source

@pytest.fixture
def classifier():
    return Classifier("config/themes.yml")

def test_classify_by_keyword(classifier):
    source = Source(platform="test", external_id="test", title="test")
    text = "This is about chemistry and music"
    themes = classifier.classify(text, None, source)
    assert "chemistry" in themes
    assert "music" in themes

def test_theme_override(classifier):
    source = Source(platform="test", external_id="test", title="test", theme_override=MagicMock(name="chemistry"))
    themes = classifier.classify("any text", None, source)
    assert themes == ["chemistry"]