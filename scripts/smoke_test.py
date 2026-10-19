"""Call every client method against the real API and print the results.

Usage:
    cp .env.example .env   # then put your key in .env
    python scripts/smoke_test.py

Unlike the test suite (which mocks HTTP), this hits the live API and uses your quota.
"""

import datetime
import os
import sys
from collections.abc import Callable
from itertools import islice
from typing import Any

from dotenv import load_dotenv

import bibleql

load_dotenv()  # reads .env into os.environ (existing env vars win), like Dotenv.load in Ruby

failures = 0


def check(label: str, call: Callable[[], Any]) -> None:
    global failures
    try:
        print(f"✅ {label}: {call()}")
    except bibleql.BibleQLError as e:
        failures += 1
        print(f"❌ {label}: {type(e).__name__}: {e}")


def expect_error(label: str, error_class: type[Exception], call: Callable[[], Any]) -> None:
    global failures
    try:
        call()
    except error_class as e:
        print(f"✅ {label}: raised {type(e).__name__} ({e})")
    else:
        failures += 1
        print(f"❌ {label}: expected {error_class.__name__}, nothing was raised")


def main() -> int:
    api_url = os.environ.get("BIBLEQL_API_URL", bibleql.client.DEFAULT_API_URL)
    print(f"BibleQL {bibleql.__version__} → {api_url}\n")

    # Client() reads BIBLEQL_API_KEY from the environment, which load_dotenv() filled in.
    with bibleql.Client(api_url=api_url) as c:
        check("passage", lambda: c.passage("John 3:16").text[:60])
        check("passage (es)", lambda: c.passage("Mateo 28:18-20", translation="spa-bes").reference)
        check("verse", lambda: c.verse("MAT", 5, 3).text[:60])
        check("chapter", lambda: f"{len(c.chapter('GEN', 1))} verses")
        check("random_verse", lambda: c.random_verse(testament="NT").book_id)
        check("random_verse books", lambda: c.random_verse(books=["PSA", "PRO"]).book_id)
        check(
            "verse_of_the_day",
            lambda: c.verse_of_the_day(date=datetime.date(2026, 1, 1)).reference,
        )
        check(
            "search",
            lambda: [f"{v.book_id} {v.chapter}:{v.verse}" for v in c.search("love", limit=3)],
        )
        check(
            "semantic_search",
            lambda: [
                (r.verse.book_name, r.verse.chapter, r.verse.verse, r.similarity)
                for r in c.semantic_search("fe y esperanza", limit=2)
            ],
        )
        check("translations", lambda: f"{len(c.translations())} translations")
        check("translation", lambda: c.translation("eng-web").name)
        check("languages", lambda: f"{len(c.languages())} languages")
        check("books", lambda: f"{len(c.books())} books")
        check("bible_index", lambda: f"{len(c.bible_index())} books")
        check(
            "concordance",
            lambda: c.concordance("misericordia", translation="spa-rv1909", first=2).total_count,
        )
        check(
            "iter_concordance",
            lambda: len(
                list(islice(c.iter_concordance("misericordia", translation="spa-rv1909"), 120))
            ),
        )
        check(
            "concordance_index",
            lambda: [
                e.lemma
                for e in c.concordance_index(translation="spa-rv1909", prefix="mis", first=3)
            ],
        )
        expect_error("unknown book", bibleql.NotFoundError, lambda: c.verse("XYZ", 1, 1))
        expect_error("unknown translation", bibleql.NotFoundError, lambda: c.translation("xxx"))
        expect_error("bad testament", bibleql.QueryError, lambda: c.random_verse(testament="ZZ"))

    with bibleql.Client(api_key="invalid-key", api_url=api_url) as bad:
        expect_error("invalid api key", bibleql.AuthenticationError, bad.books)

    print(f"\n{'All good!' if failures == 0 else f'{failures} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
