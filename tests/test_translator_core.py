import pytest
from translator_core import is_complete_sentence, clean_language_name

def test_is_complete_sentence():
    assert is_complete_sentence('This is a test.') is True
    assert is_complete_sentence('This is a long enough sentence') is True
    assert is_complete_sentence('Too short') is False
    assert is_complete_sentence('') is False

def test_clean_language_name():
    assert clean_language_name('🇺🇸 English (American)') == 'English'
    assert clean_language_name('🇲🇽 Spanish (Google only)') == 'Spanish'
    assert clean_language_name('Mandarin Chinese') == 'Chinese'
    assert clean_language_name('Brazilian Portuguese') == 'Portuguese'
    assert clean_language_name('Just Language') == 'Just Language'