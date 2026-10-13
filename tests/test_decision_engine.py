import decision_engine as de


def test_parse_json_reply_plain():
    assert de.parse_json_reply('{"a": 1}') == {"a": 1}


def test_parse_json_reply_strips_fences_and_trailing_text():
    text = '```json\n{"classification": "Hot"}\n```\nthanks'
    assert de.parse_json_reply(text) == {"classification": "Hot"}


def test_normalize_fills_missing_keys_and_label():
    out = de.normalize_classification({"classification": "hot", "budget": "50k"})
    assert out["classification"] == "Hot"
    assert out["budget"] == "50k"
    assert out["barrier"] == ""


def test_normalize_unknown_label_falls_back_to_cold():
    assert de.normalize_classification({"classification": "Maybe"})["classification"] == "Cold"
    assert de.normalize_classification({})["classification"] == "Cold"


def test_normalize_none_values_become_empty_strings():
    out = de.normalize_classification({"classification": "Warm", "budget": None})
    assert out["budget"] == ""
