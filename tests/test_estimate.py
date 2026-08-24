"""Tests for the token estimator.

This file did not exist for the whole of the estimator's first life, which is
how a constant that had never been measured survived being described as a
measurement, and how CJK -- the one script the author actually writes
documentation in -- went entirely unexercised.

The CJK cases carry most of the weight here. A Latin ratio applied to Chinese
under-counts by a factor of three, and the sub-script differences are large
enough to matter on their own: traditional Chinese costs 44% more per character
than simplified, because the tokenizer has far fewer merges for it.

Nothing here re-derives the ratios; `docs/calibrate.py` does that against a
real tokenizer. These tests pin the *behaviour* those ratios are supposed to
produce, so that a future edit that quietly breaks script detection fails here
rather than in somebody's report.
"""

import pytest

from contextcost.estimate import (
    CJK_HAN_SIMPLIFIED,
    CJK_HAN_TRADITIONAL,
    ERROR_BOUND,
    _traditional_share,
    estimate_tokens,
    looks_binary,
)

SIMPLIFIED = "这个工具用来测量代码仓库让人工智能编程助手读取时的成本，它会找出哪些文件在浪费预算。"
TRADITIONAL = "這個工具用來測量程式碼倉庫讓人工智慧編程助手讀取時的成本，並且找出哪些檔案在浪費預算。"
JAPANESE = (
    "このツールはリポジトリをコーディングエージェントが読むときのコストを測定します。"
)
KOREAN = "이 도구는 저장소를 코딩 에이전트가 읽는 데 드는 비용을 측정합니다."
ENGLISH = "This tool measures what a repository costs a coding agent to read. "


def test_empty_text_costs_nothing():
    estimate = estimate_tokens("")
    assert estimate.tokens == 0
    assert estimate.characters == 0


def test_whitespace_is_charged_because_a_real_tokenizer_charges_it():
    """This test first asserted zero, which felt obviously right and was
    wrong: `cl100k_base` encodes `"   \\n\\t  "` as 2 tokens, and the estimator
    independently says 2. Indentation in a large source tree is not free, and
    a tool that treated it as free would under-count every Python repository."""
    assert estimate_tokens("   \n\t  ").tokens == 2


def test_any_real_content_costs_at_least_one_token():
    assert estimate_tokens("a").tokens == 1


def test_chinese_is_not_charged_the_latin_rate(tmp_path=None):
    """The failure this exists to prevent. Charging Chinese at four characters
    per token under-counts it roughly threefold, and a repository with Chinese
    documentation would be told it costs a third of what it does."""
    chinese = estimate_tokens(SIMPLIFIED * 4).tokens
    naive_latin = len(SIMPLIFIED * 4) / 4.14
    assert chinese > naive_latin * 2.5


def test_chinese_is_roughly_one_token_per_character():
    text = SIMPLIFIED * 4
    per_character = estimate_tokens(text).tokens / len(text)
    assert 0.9 < per_character < 1.4


def test_traditional_chinese_costs_more_than_simplified():
    """44% more per character, measured. Both sentences say the same thing and
    are within a character of the same length, so the difference is the script
    rather than the content."""
    simplified = estimate_tokens(SIMPLIFIED * 4).tokens
    traditional = estimate_tokens(TRADITIONAL * 4).tokens
    assert traditional > simplified * 1.25
    assert CJK_HAN_TRADITIONAL > CJK_HAN_SIMPLIFIED


def test_traditional_text_is_detected_as_traditional():
    assert _traditional_share(TRADITIONAL * 3) > 0.1


def test_simplified_text_is_not_detected_as_traditional():
    """Regression, and an embarrassing one. The first traditional-character
    set included `程`, `件`, `理`, `慧` and `算`, which are written identically
    in both scripts. Simplified prose therefore tripped the traditional
    detector and was over-estimated by 41% -- worse than the single constant
    the whole change was meant to improve on.
    """
    assert _traditional_share(SIMPLIFIED * 3) == 0.0
    for word in ("编程", "文件", "处理", "智慧", "计算"):
        assert _traditional_share(word * 8) == 0.0


def test_japanese_and_korean_are_counted_as_cjk():
    for text in (JAPANESE, KOREAN):
        estimate = estimate_tokens(text * 4)
        naive_latin = len(text * 4) / 4.14
        assert estimate.tokens > naive_latin * 1.8


def test_kana_is_cheaper_per_character_than_traditional_han():
    """They are not interchangeable, which is the entire reason the ratio is
    per-script rather than one number for 'CJK'."""
    kana = "このツールはリポジトリをよむときのコストをそくていします" * 5
    han = "這個工具用來測量程式碼倉庫讀取時的成本並且找出檔案" * 5
    assert estimate_tokens(kana).tokens / len(kana) < estimate_tokens(han).tokens / len(
        han
    )


def test_mixed_chinese_and_code_charges_each_part_properly():
    """The common real case: a source file with Chinese comments."""
    mixed = "# 读取配置文件\ndef parse(path):\n    return open(path).read()\n" * 10
    estimate = estimate_tokens(mixed)
    ascii_only = (
        "# read the config file\ndef parse(path):\n    return open(path).read()\n" * 10
    )
    assert estimate.tokens > estimate_tokens(ascii_only).tokens


def test_english_is_unaffected_by_the_cjk_path():
    """A guard against fixing CJK by breaking everything else."""
    per_character = estimate_tokens(ENGLISH * 20).tokens / len(ENGLISH * 20)
    assert 0.18 < per_character < 0.28


def test_prose_and_code_are_classified_apart():
    prose = "The quick brown fox jumps over the lazy dog and keeps running. " * 20
    code = "def add(a, b):\n    return {'x': a + b, 'y': [a, b]}\n" * 20
    assert estimate_tokens(prose).kind == "prose"
    assert estimate_tokens(code).kind == "code"


# A numeric data dump: thousands of small integers, the shape of a recorded
# plotly.js fixture that started this class. Digits dominate, letters are
# only the JSON scaffolding.
_NUMERIC_MATRIX = (
    "{\n"
    + ",\n".join(
        "  [" + ", ".join(str((i * 7 + j) % 10) for j in range(12)) + "]"
        for i in range(80)
    )
    + "\n}"
)


def test_numeric_data_dump_is_its_own_class():
    assert _NUMERIC_MATRIX.count("0") > 90
    assert estimate_tokens(_NUMERIC_MATRIX).kind == "numeric"


def test_numeric_data_costs_far_more_than_the_code_ratio_assumed():
    """The regression this class exists for: charged at 4.14 chars/token, a
    small-integer matrix under-counts by roughly a factor of three against
    cl100k_base, because a byte-pair encoder merges digits poorly."""
    naive_code = len(_NUMERIC_MATRIX) / 4.14
    assert estimate_tokens(_NUMERIC_MATRIX).tokens > naive_code * 1.5


def test_numeric_ratio_rises_as_digits_dominate_more():
    sparse = "[1]" * 400
    dense = "[" + ", ".join("7" for _ in range(800)) + "]"
    per_char_sparse = estimate_tokens(sparse).tokens / len(sparse)
    per_char_dense = estimate_tokens(dense).tokens / len(dense)
    assert per_char_dense > per_char_sparse


def test_number_heavy_but_word_shaped_source_stays_code():
    """A test file full of coordinates is still prose-shaped to an agent if it
    carries as many letters as digits; the third guard keeps it out of the
    numeric class, where its words would be billed as if they were digits."""
    code = (
        "assert point.x == 100\nassert point.y == 200\n"
        "result.append(compute(point, limit))\n" * 30
    )
    assert estimate_tokens(code).kind != "numeric"


def test_prose_with_figures_is_never_numeric():
    prose = (
        "In 1997 the team measured 42 samples and reported a 3.4 percent shift. "
        "The 2011 survey repeated this with 88 sites across 12 regions and the "
        "follow-up studies across 205 fields confirmed the earlier findings in full. "
        "A second independent analysis in 2014 revisited the original sites again. " * 8
    )
    assert estimate_tokens(prose).kind == "prose"


def test_long_decimal_floats_do_not_overshoot():
    """Long decimal fractions tokenize better than their digit share predicts,
    which is what NUMERIC_MAX_RATIO caps. Without the cap this fixture family
    over-counted by ~70%."""
    floats = ",\n".join(f"{(i * 7919 % 20000) / 10000:.17g}" for i in range(300))
    estimate = estimate_tokens(floats)
    assert estimate.kind == "numeric"
    # Capped at 2.2 chars/token; the real cost is about half that, but far
    # above the 4.14 the old code path assumed.
    assert len(floats) / estimate.tokens <= 2.21


def test_opaque_content_costs_far_more_per_character_than_source():
    """Base64 has nothing for a byte-pair encoder to merge. Getting this
    backwards would under-count exactly the files the tool exists to find."""
    import base64

    blob = base64.b64encode(bytes(range(256)) * 40).decode()
    code = "def add(a, b):\n    return a + b\n" * 40
    assert estimate_tokens(blob).kind == "dense"
    assert (
        estimate_tokens(blob).tokens / len(blob)
        > estimate_tokens(code).tokens / len(code) * 1.5
    )


def test_the_error_band_brackets_the_estimate():
    estimate = estimate_tokens(ENGLISH * 20)
    assert estimate.low < estimate.tokens < estimate.high
    assert estimate.high - estimate.tokens == pytest.approx(
        estimate.tokens * ERROR_BOUND, rel=0.05
    )


def test_the_estimate_serialises_with_its_band():
    payload = estimate_tokens(ENGLISH * 5).as_dict()
    assert payload["low"] <= payload["tokens"] <= payload["high"]
    assert payload["kind"] in {"prose", "code", "dense"}


def test_binary_detection_uses_nul_bytes_like_git_does():
    assert looks_binary(b"\x89PNG\r\n\x1a\n\x00\x00") is True
    assert looks_binary(b"def add(a, b):\n    return a + b\n") is False
    assert looks_binary(b"") is False


def test_utf8_text_is_not_mistaken_for_binary():
    """High bytes are normal in any non-English repository."""
    assert looks_binary(SIMPLIFIED.encode("utf-8")) is False
    assert looks_binary(TRADITIONAL.encode("utf-8")) is False
    assert looks_binary(KOREAN.encode("utf-8")) is False
