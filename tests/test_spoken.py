from backend.board import spoken


def test_paths_become_words():
    assert spoken("In api/index.js, the path is /tmp.") == "In index dot js in the api folder, the path is the tmp folder."


def test_hindi_paths():
    assert spoken("api/index.js देखें", "hi") == "api फ़ोल्डर की index dot js फ़ाइल देखें"


def test_non_paths_untouched():
    for s in ["Answer in 5/10 words, 50/50 chance, and/or both", "Version 1.2 is out.", "<whispers> Good."]:
        assert spoken(s) == s


def test_urls_not_read_out():
    assert spoken("See https://github.com/x/y now") == "See the link now"
