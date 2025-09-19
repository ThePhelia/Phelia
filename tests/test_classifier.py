from app.services.metadata.classifier import Classifier


def test_movie_inference_from_tokens():
    classifier = Classifier()
    result = classifier.classify_torrent("Blade Runner 2049 2160p BluRay x265")
    assert result.type == "movie"
    assert result.confidence > classifier.threshold_low
    assert any(reason.startswith("title:") for reason in result.reasons)


def test_tv_detection_from_season_episode_pattern():
    classifier = Classifier()
    result = classifier.classify_torrent("Breaking.Bad.S01E02.720p.WEB-DL")
    assert result.type == "tv"
    assert result.confidence > classifier.threshold_low


def test_music_detection_with_artist_album_pattern():
    classifier = Classifier()
    result = classifier.classify_torrent("Radiohead - In Rainbows (2007) [FLAC]")
    assert result.type == "music"
    assert result.confidence > classifier.threshold_low


def test_category_hint_overrides_title_noise():
    classifier = Classifier()
    result = classifier.classify_torrent("Some Random Upload", "Audio/FLAC", None)
    assert result.type == "music"
    assert result.confidence > classifier.threshold_low


def test_indexer_prior_guides_ambiguous_title():
    classifier = Classifier()
    result = classifier.classify_torrent("Live Bootleg", None, "redacted")
    assert result.type == "music"
    assert result.confidence > 0.9


def test_indexer_dict_normalisation():
    classifier = Classifier()
    result = classifier.classify_torrent(
        "Live Bootleg",
        None,
        {"name": "Redacted", "id": "redacted"},
    )
    assert result.type == "music"
    assert result.confidence > 0.9


def test_ambiguous_title_requires_confirmation():
    classifier = Classifier()
    result = classifier.classify_torrent("Untitled Release")
    assert result.type == "other"
    assert result.confidence == 0.0
