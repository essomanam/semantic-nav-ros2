import json

from semantic_nav.command_parser import parse_command, parse_with_keywords

KNOWN = ["chair", "couch", "potted plant", "dining table"]


def test_keywords_french_with_accents():
    p = parse_with_keywords("Va vers le canapé", KNOWN)
    assert p.label == "couch" and p.criterion == "nearest"


def test_keywords_farthest():
    p = parse_with_keywords("va à la chaise la plus éloignée", KNOWN)
    assert p.label == "chair" and p.criterion == "farthest"


def test_unknown_object_returns_none():
    assert parse_with_keywords("va vers le lit", KNOWN) is None


def test_llm_answer_used_when_valid():
    llm = lambda prompt: json.dumps({"label": "potted plant", "criterion": "farthest"})
    p = parse_command("rejoins la verdure au fond", KNOWN, llm)
    assert (p.label, p.criterion, p.source) == ("potted plant", "farthest", "llm")


def test_hallucinated_label_falls_back_to_keywords():
    llm = lambda prompt: json.dumps({"label": "spaceship", "criterion": "nearest"})
    p = parse_command("va vers la chaise", KNOWN, llm)
    assert (p.label, p.source) == ("chair", "keywords")


def test_llm_failure_falls_back_to_keywords():
    def broken(prompt):
        raise TimeoutError
    assert parse_command("go to the table", KNOWN, broken).label == "dining table"
