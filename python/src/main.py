"""Main
main function and argument parsing (as applicable)
"""

from __future__ import annotations

import sys
import asyncio
import logging
import argparse

from collections import namedtuple

from typing import Callable, List

import commands

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s::%(levelname)s::%(module)s.%(funcName)s::%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

LOGGER = logging.getLogger(__file__)


BotTask = namedtuple("Task", "func args kwargs")


def construct_task(func: Callable, *args, **kwargs) -> BotTask:
    if not args:
        args = []
    if not kwargs:
        kwargs = {}
    return BotTask(func=func, args=args, kwargs=kwargs)


def argument_parsing(args: List[str]) -> argparse.Namespace:
    """Parse all arguments"""
    parser = argparse.ArgumentParser()
    return parser.parse_args(args)


def main(
    loop_tasks: List[BotTask] = None, pre_loop_tasks: List[BotTask] = None
) -> None:
    """Run main loop"""
    loop = asyncio.new_event_loop()
    if pre_loop_tasks:
        for task in pre_loop_tasks:
            loop.run_until_complete(task.func(*task.args, **task.kwargs))
    for task in loop_tasks:
        loop.create_task(task.func(*task.args, **task.kwargs))
    loop.run_forever()


if __name__ == "__main__":
    parsed_args = argument_parsing(sys.argv[1:])

    start_session = construct_task(commands.reqmgr.start_session)

    pre_loop_tasks = list()
    pre_loop_tasks.append(start_session)

    request_loop = construct_task(commands.reqmgr.loop_and_request)
    poll_database = construct_task(commands.comicbot.loop_send_updates, commands.tgbot)
    maintask = construct_task(commands.dispatcher.start_polling, commands.tgbot)

    loop_tasks = list()
    loop_tasks.append(request_loop)
    loop_tasks.append(poll_database)
    loop_tasks.append(maintask)

    main(pre_loop_tasks=pre_loop_tasks, loop_tasks=loop_tasks)
