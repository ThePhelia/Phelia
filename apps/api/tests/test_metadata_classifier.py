from app.schemas.media import Classification
from app.services.metadata.classifier import Classifier


def test_classify_torrent_returns_classification_instance():
    classifier = Classifier()
    result = classifier.classify_torrent("Untitled Release")

    assert isinstance(result, Classification)
    assert result.type == "other"
    assert result.confidence == 0.0
    assert result.reasons == []
