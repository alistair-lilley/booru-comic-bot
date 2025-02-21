"""Comic database
has an object that does stuff with the comic json
"""

from __future__ import annotations

import os
import json
import logging

from dataclasses import dataclass

from typing import Dict, List

logger = logging.getLogger(__name__)

DATADIR = "data"


@dataclass
class ComicObj:
    """One comic"""

    def __init__(self, id="", name="", pages=[], users=[]):
        self.id: int = id
        self.name: str = name
        self.pages: List[int] = pages
        self.users: List[int] = users

    def serialize(self):
        """Serialize object into a dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "pages": self.pages,
            "users": self.users,
        }


class ComicDB:
    """Objectified comic json stuff

    comics.json has the following format:

    {
        comicid: {
            "name": "comicname",
            "pages": [pagenum, ...],
            "users": [userid, ...],
        },
        ...
    }
    """

    def __init__(self: ComicDB, comics_file: str) -> None:
        self._comics_f = comics_file
        self._comics: Dict[int, ComicObj] = None

    def safe_serialize_comics(self: ComicDB) -> None:
        """Safely serialize by reloading the DB and updating it with the updates before saving"""
        updates = {**self._comics}
        self.safe_load_comics()
        self._comics.update(updates)
        self._serialize_comics()

    def _serialize_comics(self: ComicDB) -> None:
        """Serialize internal dictionary and dump to data file"""
        serialized_comics = {id: comic.serialize() for id, comic in self._comics.items()}
        with open(self._comics_f, "w") as cf:
            json.dump(serialized_comics, cf)

    def safe_load_comics(self: ComicDB) -> None:
        """Load internal dictionary from datafile, and create if it doesn't exist"""
        if not os.path.exists(self._comics_f):
            self._comics = dict()
            self._serialize_comics()
        self.load_comics()

    def load_comics(self: ComicDB) -> None:
        """Load internal dictionary from data file"""
        with open(self._comics_f) as cf:
            serialized_comics: Dict[int, str] = json.load(cf)
            self._comics = {
                id: ComicObj(**comicdict) for id, comicdict in serialized_comics.items()
            }

    def initialize_comic(self: ComicDB, comic_id: int) -> None:
        """Create empty comic object"""
        self._comics[comic_id] = ComicObj(comic_id)

    def add_user_to_comic(self: ComicDB, comic_id: int, userid: int) -> None:
        """Add a user to a comic as a watcher"""
        self._comics[comic_id].users.append(userid)

    def user_follows_comic(self: ComicDB, comic_id: int, userid: int) -> bool:
        """Verify a user follows a comic"""
        return userid in self._comics[comic_id].users

    def comic_exists(self: ComicDB, comic_id: int) -> bool:
        """Verify a comic is being tracked"""
        return comic_id in self.comic_names

    def remove_user_from_comic(self: ComicDB, comic_id: int, userid: int) -> None:
        """Remove a user from following a comic"""
        self._comics[comic_id].users.remove(userid)
        if not self._comics[comic_id].users:
            self._remove_comic_from_db(comic_id)

    def set_comic_name(self: ComicDB, comic_id: int, comicname: str):
        """Set comic name"""
        self._comics[comic_id].name = comicname

    def set_comic_pages(self: ComicDB, comic_id: int, pages: List[int]):
        """Append pages to a comic"""
        self._comics[comic_id].pages = pages

    def update_db(self: ComicDB, comic_page_updates: Dict[int, List[int]], comic_name_updates: Dict[int, str]):
        """Update entire database with a dictionary"""
        for comic_id, pages in comic_page_updates.items():
            self.set_comic_pages(comic_id, pages)
        for comic_id, name in comic_name_updates.items():
            self.set_comic_name(comic_id, name)

    def _remove_comic_from_db(self: ComicDB, comic_id: int) -> None:
        del self._comics[comic_id]

    @property
    def comic_names(self):
        return self._comics.keys()

    @property
    def comics(self):
        return self._comics
