import openstates
from openstates.cli.text_extract import (
    _PAGE_FOOTER_TAIL_RE as p, _VA_LINE_PATTERNS, _clean_virginia_text,
    _clean_massachusetts_text, apply_prediff_cleaning)
assert p in _VA_LINE_PATTERNS
assert p.match("of 12") and p.match("  OF 3  ") and not p.match("of 12 months") and not p.match("of 1234")
long = "A bill text line that is long enough to clear the degenerate guard. " * 6
a, b = _clean_virginia_text(long + "\nof 12\n" + long, long + "\nof 14\n" + long, "application/pdf", "application/pdf")
assert a == b and "of 12" not in a
assert _clean_massachusetts_text("x\nof 5\ny") == "x\ny"
assert apply_prediff_cleaning("a\nof 1", "a", jurisdiction_name="Utah", is_bill=True, prior_media_type="application/pdf", cur_media_type="application/pdf") == ("a\nof 1", "a")
print("OK", openstates.__file__)
