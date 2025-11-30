from helixcommit.parser import classify_change_type, parse_commit_message


def test_parse_conventional_commit_with_breaking_footer():
    message = (
        "feat(auth)!: require MFA\n\n"
        "Introduce mandatory multi-factor authentication for admin users.\n\n"
        "BREAKING CHANGE: Admin users must configure MFA before the next login.\n"
        "Refs: #123"
    )
    parsed = parse_commit_message(message)

    assert parsed.type == "feat"
    assert parsed.scope == "auth"
    assert parsed.breaking is True
    assert parsed.breaking_descriptions == ["Admin users must configure MFA before the next login."]
    assert parsed.footers["Refs"] == ["#123"]
    assert parsed.body.startswith("Introduce mandatory")


def test_parse_non_conventional_commit_returns_defaults():
    message = "Release v1.2.3"
    parsed = parse_commit_message(message)

    assert parsed.type is None
    assert parsed.subject == "Release v1.2.3"
    assert parsed.breaking is False


def test_classify_change_type_heuristics():
    assert classify_change_type("Fix flaky tests in pipeline") == "test"
    assert classify_change_type("Improve performance of data loader") == "perf"
    assert classify_change_type("Document new configuration") == "docs"


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_parse_empty_message():
    """Empty message should return safe defaults."""
    parsed = parse_commit_message("")
    assert parsed.type is None
    assert parsed.scope is None
    assert parsed.subject == ""
    assert parsed.body == ""
    assert parsed.footers == {}
    assert parsed.breaking is False
    assert parsed.is_conventional is False


def test_parse_whitespace_only_message():
    """Whitespace-only message should be treated as empty."""
    parsed = parse_commit_message("   \n\t\n   ")
    assert parsed.type is None
    assert parsed.scope is None
    assert parsed.subject == ""
    assert parsed.is_conventional is False


def test_parse_none_message():
    """None message should be handled gracefully."""
    parsed = parse_commit_message(None)
    assert parsed.type is None
    assert parsed.subject == ""
    assert parsed.is_conventional is False


def test_parse_empty_scope():
    """Empty scope in parentheses should be treated as no scope."""
    parsed = parse_commit_message("feat(): add feature")
    assert parsed.type == "feat"
    assert parsed.scope is None  # Empty scope becomes None
    assert parsed.subject == "add feature"
    assert parsed.is_conventional is True


def test_parse_whitespace_only_scope():
    """Whitespace-only scope should be treated as no scope."""
    parsed = parse_commit_message("feat(   ): add feature")
    assert parsed.type == "feat"
    assert parsed.scope is None  # Whitespace scope becomes None
    assert parsed.subject == "add feature"
    assert parsed.is_conventional is True


def test_parse_empty_subject():
    """Empty subject after colon should be handled."""
    parsed = parse_commit_message("feat:")
    assert parsed.type == "feat"
    assert parsed.subject == ""
    assert parsed.is_conventional is True


def test_parse_whitespace_only_subject():
    """Whitespace-only subject should be stripped."""
    parsed = parse_commit_message("feat:   ")
    assert parsed.type == "feat"
    assert parsed.subject == ""
    assert parsed.is_conventional is True


def test_parse_footer_with_empty_value():
    """Footer with empty value should be handled."""
    message = "feat: add feature\n\nSome body.\n\nRefs:"
    parsed = parse_commit_message(message)
    assert parsed.footers.get("Refs") == [""]


def test_parse_footer_with_hash_reference():
    """Footer with hash reference (e.g., Fixes #123) should be parsed."""
    message = "feat: add feature\n\nSome body.\n\nFixes #123"
    parsed = parse_commit_message(message)
    assert parsed.footers.get("Fixes") == ["#123"]


def test_parse_multiline_footer_value():
    """Multi-line footer values should be concatenated."""
    message = (
        "feat: add feature\n\n"
        "Body text.\n\n"
        "Note: First line\n"
        "  continuation line\n"
        "  another continuation"
    )
    parsed = parse_commit_message(message)
    assert "Note" in parsed.footers
    note_value = parsed.footers["Note"][0]
    assert "First line" in note_value
    assert "continuation line" in note_value
    assert "another continuation" in note_value


def test_parse_unicode_in_body():
    """Unicode characters in body should be preserved."""
    message = "feat: add emoji support\n\nAdded support for émojis 🎉 and 日本語."
    parsed = parse_commit_message(message)
    assert "émojis" in parsed.body
    assert "🎉" in parsed.body
    assert "日本語" in parsed.body


def test_parse_crlf_line_endings():
    """Windows-style CRLF line endings should be normalized."""
    message = "feat: add feature\r\n\r\nBody with CRLF.\r\n\r\nRefs: #123"
    parsed = parse_commit_message(message)
    assert parsed.type == "feat"
    assert parsed.subject == "add feature"
    assert "Body with CRLF" in parsed.body
    assert parsed.footers.get("Refs") == ["#123"]


def test_parse_type_with_hyphen():
    """Type containing hyphens should be parsed correctly."""
    parsed = parse_commit_message("my-type: some subject")
    # my-type is not a known type, so it should be None
    assert parsed.type is None
    assert parsed.is_conventional is False


def test_parse_known_type_alias():
    """Type aliases should be normalized to canonical types."""
    parsed = parse_commit_message("feature: add feature")
    assert parsed.type == "feat"  # 'feature' is an alias for 'feat'
    assert parsed.is_conventional is True


def test_parse_breaking_with_empty_scope():
    """Breaking indicator with empty scope should work."""
    parsed = parse_commit_message("feat()!: breaking change")
    assert parsed.type == "feat"
    assert parsed.scope is None
    assert parsed.breaking is True
    assert parsed.subject == "breaking change"
