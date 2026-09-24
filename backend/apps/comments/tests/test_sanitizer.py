"""Unit tests for the sanitizer (no DB needed, runs under the Django runner)."""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.comments.services import sanitizer


class AllowedTagsTests(SimpleTestCase):
    def test_allowed_tags_pass_through(self):
        """Allowed tags with valid attributes survive unchanged."""
        raw = '<strong>hi</strong> <i>x</i> <code>y</code> <a href="https://a.b" title="t">l</a>'
        self.assertEqual(sanitizer.sanitize(raw), raw)

    def test_uppercase_tags_normalized(self):
        """Uppercase allowed tags are lowercased, not escaped."""
        self.assertEqual(sanitizer.sanitize("<STRONG>hi</STRONG>"), "<strong>hi</strong>")

    def test_nested_allowed_tags(self):
        """Properly nested allowed tags pass through untouched."""
        raw = "<strong><i><code>x</code></i></strong>"
        self.assertEqual(sanitizer.sanitize(raw), raw)

    def test_multiline_code_block(self):
        """Newlines inside allowed tags are preserved."""
        raw = "<code>line1\nline2</code>"
        self.assertEqual(sanitizer.sanitize(raw), raw)

    def test_plain_text_untouched(self):
        """Text with < and & is escaped without touching words."""
        self.assertEqual(
            sanitizer.sanitize("hello 1 < 2 & friends"),
            "hello 1 &lt; 2 &amp; friends",
        )

    def test_empty_string(self):
        """Empty input sanitizes to empty output."""
        self.assertEqual(sanitizer.sanitize(""), "")


class XssProtectionTests(SimpleTestCase):
    def test_script_is_escaped(self):
        """Script tags can never survive sanitizing."""
        self.assertIn("&lt;script&gt;", sanitizer.sanitize("<script>alert(1)</script>"))

    def test_javascript_href_is_stripped(self):
        """Dangerous href protocols are removed, the link text stays."""
        out = sanitizer.sanitize('<a href="javascript:alert(1)">x</a>')
        self.assertNotIn("javascript", out)
        self.assertEqual(out, "<a>x</a>")

    def test_event_attributes_stripped(self):
        """Event handler attributes are dropped from allowed tags."""
        out = sanitizer.sanitize('<strong onclick="evil()">x</strong>')
        self.assertNotIn("onclick", out)
        self.assertEqual("<strong>x</strong>", out)

    def test_img_tag_escaped(self):
        """Images are not allowlisted and render as inert text."""
        out = sanitizer.sanitize('<img src="x" onerror="evil()">')
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)


class TagBalanceTests(SimpleTestCase):
    def test_unclosed_tag_raises(self):
        """A missing closing tag aborts sanitizing with an error."""
        with self.assertRaises(sanitizer.UnclosedTagError):
            sanitizer.sanitize("<strong>oops")

    def test_mismatched_tags_raise(self):
        """Cross-nested tags abort sanitizing with an error."""
        with self.assertRaises(sanitizer.UnclosedTagError):
            sanitizer.sanitize("<strong><i></strong></i>")

    def test_deeply_unclosed_raises(self):
        """An unclosed outer tag aborts even with a closed inner one."""
        with self.assertRaises(sanitizer.UnclosedTagError):
            sanitizer.sanitize("<strong><i>text</i>")

    def test_stray_closing_raises(self):
        """A closing tag without an opener aborts sanitizing."""
        with self.assertRaises(sanitizer.UnclosedTagError):
            sanitizer.sanitize("text</i>")
