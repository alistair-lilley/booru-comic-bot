"""BooruInterface
Interface for interacting with booru sites"""

from __future__ import annotations

import re
import logging
import urllib.parse

from typing import Dict, List, Tuple, Any, TYPE_CHECKING

from enum import IntEnum
from difflib import SequenceMatcher
from dotenv import dotenv_values

if TYPE_CHECKING:
    from comic_database import ComicObj
    from request_manager import RequestManager

LOGGER = logging.getLogger(__file__)

config = dotenv_values(".env")

POST_BASE_URL = config["POST_BASE_URL"]
POOL_BASE_URL = config["POOL_BASE_URL"]
SEARCH_BASE_URL = config["SEARCH_BASE_URL"]


class Priority(IntEnum):
    SCHEDULED = 1
    USER = 2


class BooruInterface:
    def __init__(self: BooruInterface, request_manager: RequestManager):
        self._request_manager = request_manager

    async def fetch_search(self: BooruInterface, rawquery: str) -> Dict[str, Any]:
        quoted_query = urllib.parse.quote(rawquery)
        formedquery = f"{SEARCH_BASE_URL}{quoted_query}"
        search_results = await self._request_manager.run_get_request(
            formedquery, priority=Priority.USER
        )
        return search_results

    async def fetch_pool(self: BooruInterface, comic_id: str):
        comic_data = self._request_manager.run_get_request(
            f"{POOL_BASE_URL}{comic_id}.json"
        )
        return comic_data

    async def _check_updates(
        self: BooruInterface, curr_comics: Dict[str, ComicObj]
    ) -> Dict[str, List[int]]:
        """checks all comics for updates,
        returns any updates in the form of Dict[comicid, List[pageids]]"""
        updated_pages = dict()
        full_updates = dict()
        for comic_id, comicobj in curr_comics.items():
            try:
                resp = await self._request_manager.run_get_request(
                    f"{POOL_BASE_URL}{comic_id}.json", Priority.SCHEDULED
                )
                all_posts = resp["post_ids"]
                update_pages = sorted(list(set(all_posts) - set(comicobj.pages)))

                if not update_pages:
                    continue

                curr_comics[comic_id].pages = sorted(all_posts)
                curr_comics[comic_id] = resp["name"] + (
                    "(INACTIVE) " if not resp["is_active"] else ""
                )
                updated_pages[comic_id] = update_pages

                full_updates[comic_id] = resp

            except:
                LOGGER.critical("Failed to fetch updates for comic %s", comic_id)

        if updated_pages:
            LOGGER.info("Updates found for these comics: %s", updated_pages)

        return updated_pages, full_updates

    async def check_fetch_updates(
        self: BooruInterface, curr_comics: Dict[str, ComicObj]
    ) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, Any]]:
        """Check and send updates, or return None if no updates
        Returns a dictionary in form
        {
            comic_id:
            {
                users: [...],
                pages: [...],
            }
        }
        Also update all comics with updates
        """
        while True:
            update_pages, full_updates = await self._check_updates(curr_comics)
            if update_pages:
                comics_updates_pages = await self._fetch_pages(update_pages)
                return (
                    self._pair_users_to_comics(curr_comics, comics_updates_pages),
                    full_updates,
                )
            return None

    async def _fetch_pages(
        self: BooruInterface,
        updates: Dict[str, List[int]],
    ):
        page_data = dict()

        for comic_id, page_ids in updates.items():
            page_data[comic_id] = {
                comic_id: [
                    (await self._request_manager.run_get_request(
                        f"{POST_BASE_URL}{id}.json", Priority.SCHEDULED
                    ))["post"]["sample"]["url"]
                    for id in page_ids
                ]
            }

        return page_data

    def _pair_users_to_comics(
        self: BooruInterface,
        curr_comics: Dict[str, ComicObj],
        updates: Dict[str, List[str]],
    ) -> Dict[int, Dict[str, List[int]]]:
        comics_to_users_updates = {comic_id: dict() for comic_id in curr_comics.keys()}

        import pdb; pdb.set_trace()

        for comic_id in updates.keys():
            comics_to_users_updates[comic_id]["users"] = curr_comics[comic_id].users
            comics_to_users_updates[comic_id]["pages"] = updates[comic_id]

        return comics_to_users_updates

    def _format_options(self, comics: List[Dict]) -> List[str]:
        results = []
        for comic in comics:
            results.append(re.sub("_", " ", f"{comic['name']} ({comic['id']})"))
        return results

    def _pick_closer_string(
        self: BooruInterface, current: str, challenger: str, target: str
    ) -> bool:
        curr_ratio = SequenceMatcher(None, current["name"], target).ratio()
        newratio = SequenceMatcher(None, challenger["name"], target).ratio()
        return newratio > curr_ratio

    async def _find_closest_matches(
        self: BooruInterface, comic_name: str, results: List[Dict], max_topn: int = 5
    ) -> Dict[str, str]:
        """Search by name, collecting the top N similar results"""
        topn = []
        for comicjson in await results:
            if len(topn) < max_topn:
                topn.append(comicjson)
            elif self._pick_closer_string(topn[0], comicjson, comic_name):
                topn.append(comicjson)
                topn.sort(
                    key=lambda comic: SequenceMatcher(
                        None, comic["name"], comic_name
                    ).ratio(),
                    reverse=True,
                )
                topn = topn[:max_topn]
        for comic in topn:
            comic["name"] = re.sub("_", " ", comic["name"])
            if not comic["is_active"]:
                comic["name"] = "(INACTIVE) " + comic["name"]
        return {comic["id"]: comic["name"] for comic in topn}
