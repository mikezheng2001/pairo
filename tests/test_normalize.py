from pairo.normalize import normalize_company_name


def test_strips_legal_suffix():
    assert normalize_company_name("Apple Inc.") == "apple"
    assert normalize_company_name("Apple Inc") == "apple"
    assert normalize_company_name("Apple Corp.") == "apple"


def test_lowercases_and_strips_punct():
    assert normalize_company_name("AT&T, Inc.") == "at t"  # & turned into space


def test_drops_holdings_and_group():
    assert normalize_company_name("Berkshire Hathaway Holdings, Inc.") == "berkshire hathaway"
    assert normalize_company_name("Vanguard Group") == "vanguard"


def test_intl_becomes_blank_token_dropped():
    # "INTL Globex Inc" -> drop INTL + Inc, keep globex
    assert normalize_company_name("INTL Globex Inc") == "globex"


def test_empty_input():
    assert normalize_company_name("") == ""


def test_collapses_whitespace():
    assert normalize_company_name("  Foo   Bar  ") == "foo bar"
