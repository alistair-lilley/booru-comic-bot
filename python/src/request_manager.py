"""Request manager
Queues/schedules requests sent to a booru site and manages their returns
Primarily used to ensure rate limiting isn't a problem
"""

from __future__ import annotations

import logging
import asyncio
import aiohttp

from dataclasses import dataclass, field
from typing import Any, Dict
from queue import PriorityQueue
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

config = dotenv_values(".env")

USERNAME = config["USERNAME"]
APIKEY = config["APIKEY"]
USERAGENT = config["USERAGENT"]

ATTEMPT_MAX = 3
HALF_RATE_LIMIT = 1 / 2


class PromiseBreakException(BaseException):
    """Exception when a Promise is broken"""

    pass


@dataclass(order=True)
class PrioritizedRequest:
    """Used to enable prioritizing requests"""

    priority: int
    request: str = field(compare=False)
    promise: PromisedResponse = field(compare=False)


class PromisedResponse:
    """Promised response for a request that has been enqueued"""

    def __init__(self: PromisedResponse) -> None:
        self.complete: bool = False
        self._return_value: Dict = None
        self.promise_broken: bool = False

    def fulfill(self: PromisedResponse, completion: Dict) -> None:
        """Set return value and confirm promise is complete"""
        self._return_value = completion
        self.complete = True

    def break_promise(self: PromisedResponse) -> None:
        """Set no return value, note that promise has been broken"""
        self.promise_broken = True

    async def wait_for_promised_request(self: PromisedResponse) -> Any:
        """Wait until promise is marked as complete, then return completed value unless
        promise has been broken
        """
        while not self.complete:
            try:
                assert not self.promise_broken
            except AssertionError:
                raise (PromiseBreakException("Could not fulfill request promise"))
            await asyncio.sleep(0)
        return self._return_value


class RequestManager:
    """A queueing manager that accepts AIOHTTP requests to a booru site and ensures that only 2
    requests per second are sent, preventing rate limiting problems
    """

    def __init__(self: RequestManager) -> None:
        self._request_queue = PriorityQueue()
        self._aiohttp_session: aiohttp.ClientSession = None
        self._auth = None
        self._header = None

    async def start_session(self: RequestManager) -> None:
        """Start an aiohttp session
        We don't want to have to create one every single time a request is called, so we're just
        going to create one here and reuse it everywhere
        """
        self._auth = aiohttp.BasicAuth((USERNAME, APIKEY))
        self._header = {"user-agent": USERAGENT}
        self._aiohttp_session = aiohttp.ClientSession()

    async def run_get_request(
        self: RequestManager, request: Any, priority: int
    ) -> Dict:
        """Enqueues a request and waits for the promised result"""
        promise = self._enq_req(request, priority)
        return await promise.wait_for_promised_request()

    def _enq_req(self: RequestManager, request: Any, priority: int) -> PromisedResponse:
        logger.info(f"enqueued request: <{request}> at priority level: {priority}")
        reqprom = PromisedResponse()
        self._request_queue.put(
            PrioritizedRequest(priority=priority, request=request, promise=reqprom)
        )
        return reqprom

    async def _run_one_request(
        self: RequestManager, request_to_run: PrioritizedRequest, attempt: int
    ):
        logger.info(f"Requesting page <{request_to_run.request}>; attempt {attempt}")
        async with self._aiohttp_session.get(
            request_to_run.request,
            auth=self._auth,
            headers=self._header,
        ) as resp:
            try:
                request_to_run.promise.fulfill(await resp.json())
            except Exception as e:
                if attempt == ATTEMPT_MAX:
                    logger.critical(f"Fetching request failed due to error {e}")
                    request_to_run.promise.break_promise()
                else:
                    logger.warning(
                        f"Fetch attempt {attempt} for request <{request_to_run.request}> failed; "
                        f"retrying in {HALF_RATE_LIMIT + 0.01} seconds"
                    )

    async def loop_and_request(self: RequestManager) -> None:
        """Continually loops through queue and runs each request in priority order"""
        logger.info("Beginning request loop")
        while True:
            if self._request_queue.empty():
                await asyncio.sleep(0)
                continue
            request_to_run: PrioritizedRequest = self._request_queue.get()
            for attempt in range(1, ATTEMPT_MAX + 1):
                await self._run_one_request(request_to_run, attempt)
                await asyncio.sleep(HALF_RATE_LIMIT + 0.01)  # Add 0.01 just to be safe
                if (
                    request_to_run.promise.complete
                    or request_to_run.promise.promise_broken
                ):
                    break
