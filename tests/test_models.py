import dataclasses

import pytest

from bibleql.models import (
    Book,
    Chapter,
    Language,
    LocalizedBook,
    Passage,
    SemanticSearchResult,
    Translation,
    Verse,
)

VERSE_DATA = {
    "bookId": "JHN",
    "bookName": "John",
    "chapter": 3,
    "verse": 16,
    "text": "For God so loved the world...",
}


def test_verse_from_api():
    verse = Verse.from_api(VERSE_DATA)

    assert verse.book_id == "JHN"
    assert verse.book_name == "John"
    assert verse.chapter == 3
    assert verse.verse == 16
    assert verse.text == "For God so loved the world..."


def test_verses_with_same_data_are_equal():
    assert Verse.from_api(VERSE_DATA) == Verse.from_api(VERSE_DATA)


def test_verse_is_immutable():
    verse = Verse.from_api(VERSE_DATA)

    with pytest.raises(dataclasses.FrozenInstanceError):
        verse.text = "changed"


def test_verse_as_dict():
    verse = Verse.from_api(VERSE_DATA)

    assert dataclasses.asdict(verse)["book_id"] == "JHN"


def test_passage_from_api_builds_nested_verses():
    passage = Passage.from_api(
        {
            "reference": "John 3:16",
            "translationId": "eng-web",
            "translationName": "World English Bible",
            "translationNote": None,
            "text": "For God so loved the world...",
            "verses": [VERSE_DATA],
        }
    )

    assert passage.reference == "John 3:16"
    assert passage.translation_note is None
    assert passage.verses == [Verse.from_api(VERSE_DATA)]


def test_passage_without_verses_defaults_to_empty_list():
    passage = Passage.from_api(
        {
            "reference": "John 3:16",
            "translationId": "eng-web",
            "translationName": "World English Bible",
            "text": "For God so loved the world...",
        }
    )

    assert passage.verses == []
    assert passage.translation_note is None


def test_book_from_api():
    book = Book.from_api({"bookId": "GEN", "name": "Genesis", "testament": "OT", "position": 1})

    assert book == Book(book_id="GEN", name="Genesis", testament="OT", position=1)


def test_localized_book_from_api_builds_chapters():
    book = LocalizedBook.from_api(
        {
            "bookId": "GEN",
            "name": "Génesis",
            "testament": "OT",
            "position": 1,
            "chapterCount": 50,
            "chapters": [{"number": 1, "verseCount": 31}],
        }
    )

    assert book.chapter_count == 50
    assert book.chapters[0].number == 1
    assert book.chapters[0].verse_count == 31


def test_chapter_from_api_with_and_without_verses():
    assert Chapter.from_api({"number": 1, "verseCount": 31}).verses == []

    chapter = Chapter.from_api({"number": 3, "verseCount": 36, "verses": [VERSE_DATA]})
    assert chapter.verses == [Verse.from_api(VERSE_DATA)]


def test_translation_from_api():
    translation = Translation.from_api(
        {
            "identifier": "eng-web",
            "name": "World English Bible",
            "language": "eng",
            "abbrev": "WEB",
            "languageName": "English",
            "note": None,
            "books": [
                {
                    "bookId": "GEN",
                    "name": "Genesis",
                    "testament": "OT",
                    "position": 1,
                    "chapterCount": 50,
                }
            ],
        }
    )

    assert translation.identifier == "eng-web"
    assert translation.abbrev == "WEB"
    assert translation.language_name == "English"
    assert translation.note is None
    assert isinstance(translation.books[0], LocalizedBook)
    assert translation.books[0].chapter_count == 50


def test_translation_without_optional_fields():
    translation = Translation.from_api(
        {"identifier": "eng-web", "name": "World English Bible", "language": "eng"}
    )

    assert translation.abbrev is None
    assert translation.language_name is None
    assert translation.books == []


def test_language_from_api():
    language = Language.from_api(
        {
            "code": "eng",
            "translationCount": 2,
            "translations": [
                {"identifier": "eng-web", "name": "World English Bible", "language": "eng"},
                {"identifier": "eng-kjv", "name": "King James Version", "language": "eng"},
            ],
        }
    )

    assert language.code == "eng"
    assert language.translation_count == 2
    assert isinstance(language.translations[0], Translation)
    assert [t.identifier for t in language.translations] == ["eng-web", "eng-kjv"]


def test_semantic_search_result_from_api():
    result = SemanticSearchResult.from_api({"verse": VERSE_DATA, "similarity": 0.95})

    assert isinstance(result.verse, Verse)
    assert result.verse.book_id == "JHN"
    assert result.similarity == 0.95
