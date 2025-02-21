"""comic tracker
I keep track of each comic and what pages are available for it!
"""

from __future__ import annotations

import logging

from typing import Dict, List,  TYPE_CHECKING
from enum import IntEnum

from comic_database import ComicObj

if TYPE_CHECKING:
    from comic_database import ComicDB

logger = logging.getLogger(__name__)

DATADIR = "data"


class RequestPriority(IntEnum):
    """Priority marker for requests"""

    SCHEDULED = 1
    USER = 2


class ComicTracker:
    """Comic tracker!
    This nifty little object is going to keep track of the comics that are being tracked,
    including their pages and all!
    it will keep track of the comics both in memory and in data/comics.json
    """

    def __init__(
        self: ComicTracker,
        comic_db: ComicDB,
    ) -> None:
        self._comics_db: ComicDB = comic_db
        self._comics_db.safe_load_comics()

    async def dump_updates(
        self: ComicTracker, pageupdates, nameupdates
    ) -> Dict[str, List[int]]:
        """checks comics for updates, saves them, and returns them for sending"""
        self._comics_db.update_db(pageupdates, nameupdates)
        self._comics_db.safe_serialize_comics()
        return pageupdates

    def get_comic_names(self: ComicTracker) -> List[str]:
        """Gets the name of each comic in a list"""
        return self._comics_db.comic_names

    def get_comic_name(self: ComicTracker, comic_id: str) -> str:
        """Gets the name of one comic"""
        return self._comics_db.comics[comic_id].name

    def add_user_to_comic(self: ComicTracker, user_id: str, comic_id: str) -> bool:
        """Add comic, then save; return True if the comic is new"""
        if comic_id in self.comics:
            self._comics_db.add_user_to_comic(comic_id, user_id)
            return False
        self.comics[comic_id] = ComicObj(id=comic_id, users=[user_id])
        self._comics_db.safe_serialize_comics()
        return True

    def remove_user_from_comic(self: ComicTracker, user_id: str, comic_id: str) -> None:
        """Remove comic, then save"""
        self._comics_db.remove_user_from_comic(user_id, comic_id)
        self._comics_db.safe_serialize_comics()

    def remove_from_all(self: ComicTracker, user_id: str):
        """Remove a user from all comics in the database"""
        for comic_id in self.comics.keys():
            if user_id in self.comics[comic_id].users:
                self.comics[comic_id].users.remove(user_id)
        self._comics_db.safe_serialize_comics()

    def fetch_users_comics(self: ComicTracker, user_id: str) -> List[Dict]:
        """Fetch all comics for a certain user"""
        users_comics = list()
        for comicdata in self.comics.values():
            if user_id in comicdata["users"]:
                users_comics.append(comicdata)
        return users_comics

    def update_comic(self: ComicTracker, comic_id: int, comic_data: Dict) -> None:
        """Update the pages and name of a comic"""
        self._comics_db.set_comic_name(comic_id, comic_data["name"])
        self._comics_db.set_comic_pages(comic_id, comic_data["post_ids"])

    @property
    def comics(self: ComicTracker):
        return self._comics_db.comics
