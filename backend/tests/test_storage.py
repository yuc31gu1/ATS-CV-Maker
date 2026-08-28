import pytest

from app.storage.base import StorageService
from app.storage.local import LocalStorageService


def test_save_load_delete_roundtrip(temp_storage: LocalStorageService):
    temp_storage.save("uploads/cv.pdf", b"%PDF-1.4")
    assert temp_storage.load("uploads/cv.pdf") == b"%PDF-1.4"
    assert temp_storage.exists("uploads/cv.pdf")
    temp_storage.delete("uploads/cv.pdf")
    assert not temp_storage.exists("uploads/cv.pdf")


def test_save_writes_nested_keys(temp_storage: LocalStorageService):
    temp_storage.save("latex/generated/0001.tex", b"\\section{Resume}")
    assert temp_storage.load("latex/generated/0001.tex") == b"\\section{Resume}"


def test_save_rejects_path_escape(temp_storage: LocalStorageService):
    with pytest.raises(ValueError):
        temp_storage.save("../escape.txt", b"nope")


def test_local_storage_satisfies_storage_protocol(temp_storage: LocalStorageService):
    assert isinstance(temp_storage, StorageService)