"""Offline test helpers: a fake requests.Session plus small HTML fixtures."""
import requests


class FakeResponse:
    def __init__(self, url, text="", status=200):
        self.url, self.text, self.status_code, self.encoding = url, text, status, None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for {self.url}")


class FakeSession:
    """pages maps url -> html string, or an Exception instance to raise. Unknown url -> 404."""

    def __init__(self, pages):
        self.pages, self.requested = pages, []

    def get(self, url, timeout=None):
        self.requested.append(url)
        entry = self.pages.get(url)
        if entry is None:
            return FakeResponse(url, "", 404)
        if isinstance(entry, Exception):
            raise entry
        return FakeResponse(url, entry)


def book(href, title, price, rating):
    price_html = f'<p class="price_color">{price}</p>' if price else ""
    return (f'<article class="product_pod"><p class="star-rating {rating}"></p>'
            f'<h3><a href="{href}" title="{title}">{title[:10]}...</a></h3>'
            f'<div class="product_price">{price_html}</div></article>')


def book_detail(category, description):
    return ('<ul class="breadcrumb"><li><a href="/">Home</a></li><li><a href="#">Books</a></li>'
            f'<li><a href="#">{category}</a></li><li class="active">x</li></ul>'
            f'<div id="product_description" class="sub-header"><h2>Product Description</h2></div>'
            f'<p>{description}</p>')


def quote(text, author, tags):
    author_html = f'<small class="author">{author}</small>' if author else ""
    tags_html = "".join(f'<a class="tag" href="/tag/{t}/">{t}</a>' for t in tags)
    return (f'<div class="quote"><span class="text">{text}</span>'
            f'<span>by {author_html}<a href="/author/x">(about)</a></span>'
            f'<div class="tags">Tags: {tags_html}</div></div>')


def page(items, next_href=None):
    nxt = f'<ul class="pager"><li class="next"><a href="{next_href}">next</a></li></ul>' if next_href else ""
    return f"<html><body>{''.join(items)}{nxt}</body></html>"


B1 = "https://books.toscrape.com/"
B2 = "https://books.toscrape.com/catalogue/page-2.html"
Q1 = "https://quotes.toscrape.com/"
Q2 = "https://quotes.toscrape.com/page/2/"
EINSTEIN = "\u201cThe world as we have created it is a process of our thinking.\u201d"


def books_site():
    return {
        B1: page([book("catalogue/a-light_1000/index.html", "A Light in the Attic", "\u00a351.77", "Three"),
                  book("catalogue/tipping_999/index.html", "Tipping the Velvet", None, "One")],
                 next_href="catalogue/page-2.html"),
        B2: page([book("soumission_998/index.html", "Soumission", "\u00a350.10", "One"),
                  book("dup_1/index.html", "A LIGHT IN THE ATTIC", "\u00a351.77", "Three")]),
        "https://books.toscrape.com/catalogue/a-light_1000/index.html": book_detail("Poetry", "A poetry book."),
        "https://books.toscrape.com/catalogue/soumission_998/index.html": book_detail("Fiction", "A novel."),
        "https://books.toscrape.com/catalogue/dup_1/index.html": book_detail("Poetry", "A poetry book."),
        # tipping_999 detail page intentionally missing -> 404
    }


def quotes_site():
    return {
        Q1: page([quote(EINSTEIN, "Albert Einstein", ["change", "Deep-Thoughts"]),
                  quote("\u201cNo tags here.\u201d", "Jane Austen", []),
                  quote("\u201cNobody wrote me.\u201d", None, ["orphan"])],
                 next_href="/page/2/"),
        Q2: page([quote("\u201c  THE WORLD AS WE HAVE CREATED IT is a process of our thinking.  \u201d",
                        "Albert  Einstein", ["change"]),
                  quote("\u201cA fresh quote.\u201d", "Mark Twain", ["humor"])]),
    }
