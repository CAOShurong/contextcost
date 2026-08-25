"""Tests for the terminal report.

A report is where an honest analysis usually stops being honest: the caveats
stay in the docstrings and the reader takes away the bold number. So most of
what is checked here is not layout but whether the qualifications survived the
trip to the screen -- that the error bound is printed, that "measured" and
"estimated" are not interchanged, and that the tier the tool cannot judge is
still visibly undecided by the time it reaches a human.
"""

import io

from contextcost.estimate import ERROR_BOUND
from contextcost.reduce import reduce_repository
from contextcost.report import render, supports_unicode
from contextcost.walk import walk_repository

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
    return str(root)


def report_for(root, **kwargs):
    return render(
        walk_repository(root), reduce_repository(root, **kwargs), colour=False
    )


def test_the_error_bound_is_printed_beside_the_total(tmp_path):
    """A six-figure number from a tool with no tokenizer. Printed without its
    bound once, it gets quoted without one forever."""
    text = report_for(build(tmp_path, {"src/app.py": SOURCE}))
    assert "tokens to read this repository" in text
    assert f"{ERROR_BOUND:.0%} estimated, no tokenizer" in text


def test_the_saving_is_called_measured_and_not_estimated(tmp_path):
    text = report_for(build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE}))
    assert "Measured by walking the repository again" in text
    assert "not by subtracting what was dropped" in text


def test_the_possible_tier_reaches_the_screen_still_undecided(tmp_path):
    """It must not read as part of the result."""
    rows = "".join(f"{n},alpha,beta,gamma,delta\n" for n in range(2000))
    text = report_for(build(tmp_path, {"data/rows.csv": rows, "src/app.py": SOURCE}))
    assert "YOUR DECISION" in text
    assert "not excluded automatically" in text
    assert "--include-possible" in text
    # The rule's own reasoning, so the reader can disagree without leaving.
    assert "the file system cannot settle" in text


def test_a_narrowed_proposal_is_confessed_in_the_report(tmp_path):
    """Correcting an over-reaching pattern silently would be a quieter version
    of the bug it corrected."""
    root = build(tmp_path, {"docs/app.min.js": FILLER, "docs/guide/writing.md": FILLER})
    reduction = reduce_repository(root)
    assert reduction.narrowed_from
    text = render(walk_repository(root), reduction, colour=False)
    assert "One proposal was narrowed" in text
    assert "never proposed" in text


def test_a_clean_repository_says_it_found_nothing(tmp_path):
    text = report_for(build(tmp_path, {"src/app.py": SOURCE, "README.md": FILLER}))
    assert "Nothing proposed" in text
    assert "saved" not in text.split("SAVING")[1]


def test_binaries_are_reported_as_binaries_not_binarys(tmp_path):
    """Regression for a plural that reached a real terminal."""
    root = build(
        tmp_path,
        {
            "src/app.py": SOURCE,
            "a.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 300,
            "b.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 300,
        },
    )
    text = report_for(root)
    assert "2 binaries not counted" in text
    assert "binarys" not in text


def test_one_binary_is_singular(tmp_path):
    root = build(
        tmp_path, {"src/app.py": SOURCE, "a.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 300}
    )
    assert "1 binary not counted" in report_for(root)


def test_the_ascii_fallback_emits_nothing_outside_ascii(tmp_path):
    """The report is unreadable rather than merely ugly on a terminal that
    cannot encode the drawing characters, and `print` substitutes silently."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    text = render(
        walk_repository(root), reduce_repository(root), colour=False, unicode_ok=False
    )
    text.encode("ascii")  # raises if anything slipped through
    assert f"+/-{ERROR_BOUND:.0%}" in text
    assert "->" in text
    assert "#" in text


def test_supports_unicode_asks_the_stream_rather_than_the_platform():
    assert supports_unicode(io.TextIOWrapper(io.BytesIO(), encoding="utf-8")) is True
    assert supports_unicode(io.TextIOWrapper(io.BytesIO(), encoding="ascii")) is False


def test_colour_can_be_turned_off_completely(tmp_path):
    """Reports get piped into files and pasted into issues."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    assert "\033[" not in render(
        walk_repository(root), reduce_repository(root), colour=False
    )
    assert "\033[" in render(
        walk_repository(root), reduce_repository(root), colour=True
    )


def test_sampled_files_are_labelled_as_sampled(tmp_path):
    """A file measured from a 2 MB sample must not read as a precise count."""
    big = ("alpha beta gamma delta epsilon zeta eta theta\n") * 60000
    root = build(tmp_path, {"huge.md": big, "src/app.py": SOURCE})
    walk = walk_repository(root)
    assert any(c.sampled for c in walk.files), (
        "the fixture needs to exceed the sampling threshold"
    )
    assert "sampled" in render(walk, reduce_repository(root), colour=False)


def test_saving_names_the_consumers_real_ignore_file(tmp_path):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    walk = walk_repository(root, consumer="aider")
    reduction = reduce_repository(root, consumer="aider")

    text = render(walk, reduction, colour=False)
    assert "consumer: aider" in text
    assert "Add to .aiderignore" in text
    assert "--write-ignore" in text


def test_next_steps_appear_when_there_is_waste_to_act_on(tmp_path):
    """The report should not end at the number: the three moves that turn a
    one-shot measurement into a standing control are printed with it."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    text = report_for(root)
    assert "NEXT STEPS" in text
    assert "--write-gitignore" in text
    assert "--fail-over" in text
    assert "--badge" in text


def test_a_clean_repository_gets_no_next_steps(tmp_path):
    """No proposal means nothing to accept and no follow-up to sell."""
    root = build(tmp_path, {"src/app.py": SOURCE})
    text = report_for(root)
    assert "NEXT STEPS" not in text
