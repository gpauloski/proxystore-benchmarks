from __future__ import annotations

import pathlib
from typing import Generator

import pytest
from proxystore.connectors.file import FileConnector
from proxystore.connectors.local import LocalConnector
from proxystore.store import store_registration
from proxystore.store.base import Store

from testing.executor import ProcessPoolExecutor
from testing.executor import ThreadPoolExecutor


@pytest.fixture()
def process_executor() -> Generator[ProcessPoolExecutor, None, None]:
    with ProcessPoolExecutor(2) as executor:
        yield executor


@pytest.fixture()
def thread_executor() -> Generator[ThreadPoolExecutor, None, None]:
    with ThreadPoolExecutor(2) as executor:
        yield executor


@pytest.fixture()
def file_store(
    tmp_path: pathlib.Path,
) -> Generator[Store[FileConnector], None, None]:
    with Store(
        'file-store-fixture',
        FileConnector(str(tmp_path / 'store')),
    ) as store:
        with store_registration(store):
            yield store


@pytest.fixture()
def local_store() -> Generator[Store[LocalConnector], None, None]:
    with Store('local-store-fixture', LocalConnector()) as store:
        with store_registration(store):
            yield store
