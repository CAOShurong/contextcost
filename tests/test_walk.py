"""Tests for the repository walk.

Every number this tool prints is derived from here, so the tests are aimed at
the ways a total can be wrong while still looking plausible: counting files git
would never show, charging a PNG the text rate, treating an unreadable file as
an empty one, or quietly reading a 40 MB fixture in full and calling the result
exact.

The ordering test looks trivial and is not. `os.walk` returns entries in
whatever order the file system offers, so a report whose ties broke differently
between two runs would read as though the tool had changed its mind about a
repository that had not changed at all.
"""

from contextcost.walk import SAMPLE_ABOVE, walk_repository

SOURCE = "def add(a, b):\n    return a + b\n" * 30
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 500


def build(root, files):
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return str(root)


def paths(result):
    return [cost.path for cost in result.files]


def test_ignored_directories_are_never_descended_into(tmp_path):
    """Counting `.venv/` would make every repository look identically enormous
    and the report worthless."""
    root = build(
        tmp_path,
        {
            ".gitignore": ".venv/\n",
            ".venv/lib/big.py": SOURCE * 20,
            "src/app.py": SOURCE,
        },
    )
    result = walk_repository(root)
    # `.gitignore` is itself a file in the repository and is counted as one.
    assert paths(result) == [".gitignore", "src/app.py"]
    assert result.ignored_count == 1


def test_the_git_directory_is_skipped_whatever_the_ignore_file_says(tmp_path):
    """It is frequently larger than the working tree and never interesting."""
    root = build(tmp_path, {".git/objects/thing": SOURCE, "src/app.py": SOURCE})
    assert paths(walk_repository(root)) == ["src/app.py"]


def test_a_nested_ignore_file_anchors_to_its_own_directory(tmp_path):
    """`docs/.gitignore` saying `build/` must not hide `build/` at the root.
    Nested patterns cannot be flattened into one list up front, which is why
    the walker picks them up as it descends."""
    root = build(
        tmp_path,
        {
            "docs/.gitignore": "build/\n",
            "docs/build/generated.md": SOURCE,
            "docs/guide.md": SOURCE,
            "build/kept.py": SOURCE,
        },
    )
    found = set(paths(walk_repository(root)))
    assert "docs/build/generated.md" not in found
    assert "docs/guide.md" in found
    assert "build/kept.py" in found


def test_a_binary_is_counted_but_charged_no_tokens(tmp_path):
    """An agent does not read a PNG as text. Charging it the text rate would
    be inventing a number, so binaries are reported as a separate quantity
    that is deliberately not added to the total."""
    root = build(tmp_path, {"logo.png": PNG, "src/app.py": SOURCE})
    result = walk_repository(root)

    binary = next(c for c in result.files if c.path == "logo.png")
    assert binary.binary is True
    assert binary.tokens == 0
    assert binary.bytes == len(PNG)
    assert result.tokens == sum(c.tokens for c in result.text_files)
    assert len(result.binary_files) == 1


def test_an_empty_file_costs_nothing_without_being_skipped(tmp_path):
    root = build(tmp_path, {"__init__.py": "", "src/app.py": SOURCE})
    result = walk_repository(root)
    empty = next(c for c in result.files if c.path == "__init__.py")
    assert empty.tokens == 0
    assert empty.bytes == 0
    assert result.skipped == []


def test_a_large_file_is_sampled_and_says_so(tmp_path):
    """Reading a 40 MB generated file whole is the one thing that would make
    this slow on the repositories that most need it. Extrapolating is honest
    only because the result is labelled."""
    big = "alpha beta gamma delta epsilon zeta\n" * 120000
    root = build(tmp_path, {"huge.md": big})
    cost = walk_repository(root).files[0]

    assert cost.bytes > SAMPLE_ABOVE
    assert cost.sampled is True
    # Extrapolated from the sample to the whole file, so it should land in the
    # right order of magnitude rather than reporting only what was read.
    assert cost.tokens > SAMPLE_ABOVE / 10


def test_a_small_file_is_not_marked_sampled(tmp_path):
    root = build(tmp_path, {"small.py": SOURCE})
    assert walk_repository(root).files[0].sampled is False


def test_the_walk_order_is_stable_and_not_the_file_system_order(tmp_path):
    root = build(
        tmp_path,
        {"z.py": SOURCE, "a.py": SOURCE, "m/b.py": SOURCE, "m/a.py": SOURCE},
    )
    first = paths(walk_repository(root))
    assert first == sorted(first)
    assert first == paths(walk_repository(root))


def test_extra_ignore_removes_files_without_touching_the_repository(tmp_path):
    """The argument the whole measured reduction is built on."""
    root = build(tmp_path, {"yarn.lock": SOURCE, "src/app.py": SOURCE})
    before = walk_repository(root)
    after = walk_repository(root, extra_ignore=["/yarn.lock"])

    assert after.tokens < before.tokens
    assert "yarn.lock" not in paths(after)
    assert (tmp_path / "yarn.lock").exists(), "nothing on disk may change"


def test_gitignore_can_be_switched_off(tmp_path):
    root = build(tmp_path, {".gitignore": "hidden/\n", "hidden/x.py": SOURCE})
    assert paths(walk_repository(root)) == [".gitignore"]
    assert "hidden/x.py" in paths(walk_repository(root, use_gitignore=False))


def test_cursor_and_aider_profiles_add_their_native_ignore_files(tmp_path):
    for consumer, ignore_name in (
        ("cursor", ".cursorignore"),
        ("aider", ".aiderignore"),
    ):
        case = tmp_path / consumer
        root = build(
            case,
            {
                ".gitignore": "git-only.py\n",
                ignore_name: "consumer-only.py\n",
                "git-only.py": SOURCE,
                "consumer-only.py": SOURCE,
                "src/app.py": SOURCE,
            },
        )

        result = walk_repository(root, consumer=consumer)
        found = paths(result)
        assert "git-only.py" not in found
        assert "consumer-only.py" not in found
        assert "src/app.py" in found
        assert result.consumer == consumer
        assert ignore_name in result.ignore_files


def test_repomix_profile_models_its_documented_ignore_inputs(tmp_path):
    root = build(
        tmp_path,
        {
            ".gitignore": "git-only.py\n",
            ".ignore": "dot-ignore.py\n",
            ".repomixignore": "repomix-only.py\n",
            ".git/info/exclude": "info-only.py\n",
            "git-only.py": SOURCE,
            "dot-ignore.py": SOURCE,
            "repomix-only.py": SOURCE,
            "info-only.py": SOURCE,
            "src/app.py": SOURCE,
        },
    )

    found = paths(walk_repository(root, consumer="repomix"))
    assert "src/app.py" in found
    assert not {
        "git-only.py",
        "dot-ignore.py",
        "repomix-only.py",
        "info-only.py",
    } & set(found)

    generic = paths(walk_repository(root))
    assert "dot-ignore.py" in generic
    assert "repomix-only.py" in generic
    assert "info-only.py" in generic

    without_git = paths(walk_repository(root, consumer="repomix", use_gitignore=False))
    assert "git-only.py" in without_git
    assert "info-only.py" in without_git
    assert "dot-ignore.py" not in without_git
    assert "repomix-only.py" not in without_git


def test_totals_roll_up_by_directory_and_by_extension(tmp_path):
    root = build(
        tmp_path,
        {
            "src/a.py": SOURCE,
            "src/deep/b.py": SOURCE,
            "docs/c.md": SOURCE,
            "top.py": SOURCE,
        },
    )
    result = walk_repository(root)

    directories = result.by_directory()
    assert directories["src"] == sum(
        c.tokens for c in result.text_files if c.path.startswith("src/")
    )
    assert "(root)" in directories
    # Sorted biggest first, because the actionable unit is a top-level
    # directory and the reader wants the expensive one at the top.
    assert list(directories.values()) == sorted(directories.values(), reverse=True)

    extensions = result.by_extension()
    assert set(extensions) == {".py", ".md"}
    assert sum(extensions.values()) == result.tokens


def test_largest_returns_the_most_expensive_first(tmp_path):
    root = build(
        tmp_path, {"big.py": SOURCE * 5, "small.py": SOURCE, "mid.py": SOURCE * 2}
    )
    assert [c.path for c in walk_repository(root).largest(2)] == ["big.py", "mid.py"]


def test_a_file_with_no_extension_is_grouped_rather_than_dropped(tmp_path):
    root = build(tmp_path, {"Makefile": SOURCE})
    assert "(none)" in walk_repository(root).by_extension()


def test_the_result_serialises_with_the_counts_it_reports(tmp_path):
    root = build(tmp_path, {"logo.png": PNG, "src/app.py": SOURCE})
    payload = walk_repository(root).as_dict()
    assert payload["text_files"] == 1
    assert payload["binary_files"] == 1
    assert payload["files"] == 2
    assert payload["tokens"] > 0
