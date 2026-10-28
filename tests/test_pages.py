from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.source = (ROOT / name).read_text(encoding="utf-8")
        self.elements = []
        self.feed(self.source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class PublishedPages(unittest.TestCase):
    def setUp(self):
        self.pages = [Page("index.html"), Page("privacy.html")]

    def test_pages_have_accessible_document_structure(self):
        for page in self.pages:
            with self.subTest(page=page.name):
                self.assertIn(("html", {"lang": "en"}), page.elements)
                for tag in ("title", "h1", "main", "nav"):
                    self.assertEqual(sum(t == tag for t, _ in page.elements), 1)
                self.assertTrue(any(t == "meta" and a.get("name") == "viewport"
                                    for t, a in page.elements))

    def test_links_are_https_or_resolve_to_published_pages(self):
        for page in self.pages:
            for tag, attrs in page.elements:
                if tag != "a":
                    continue
                href = attrs["href"]
                with self.subTest(page=page.name, href=href):
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        self.assertEqual(url.scheme, "https")
                        self.assertTrue(url.netloc)
                    else:
                        target = ROOT / unquote(url.path or "index.html")
                        if target.is_dir():
                            target /= "index.html"
                        self.assertIn(target.resolve(), [(ROOT / p.name).resolve() for p in self.pages])
                        self.assertTrue(target.is_file())

    def test_homepage_and_policy_are_linked(self):
        self.assertTrue(any(t == "a" and a.get("href") == "privacy.html"
                            for t, a in self.pages[0].elements))
        self.assertTrue(any(t == "a" and a.get("href") == "./"
                            for t, a in self.pages[1].elements))

    def test_privacy_requirement_no_active_or_external_resources(self):
        for page in self.pages:
            with self.subTest(page=page.name):
                for tag, attrs in page.elements:
                    self.assertNotIn(tag, {"script", "form", "iframe", "object", "embed", "img", "link"})
                    self.assertFalse(any(k.startswith("on") for k in attrs))
                self.assertNotRegex(page.source, r"(?i)url\s*\(|@import")

    def test_privacy_requirement_no_account_or_credential_details(self):
        for page in self.pages:
            with self.subTest(page=page.name):
                self.assertNotRegex(page.source, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
                self.assertNotRegex(page.source, r"/home/|/etc/|GOCSPX-|ya29\.|AIza[A-Za-z0-9_-]+")


if __name__ == "__main__":
    unittest.main()
