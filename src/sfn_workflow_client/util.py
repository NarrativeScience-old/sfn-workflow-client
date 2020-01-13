"""Utility functions"""
import asyncio
from functools import partial
from typing import Any, Callable, Iterator, List, Union


async def call_async(func: Callable, *args, **kwargs) -> Any:
    """Helper method that wraps a synchronous function in a new thread.

    Args:
        func: Function to call

    Returns:
        result of the function

    """
    return await asyncio.get_event_loop().run_in_executor(
        None, partial(func, *args, **kwargs)
    )


class Collection:
    """Represents a collection of items"""

    #: Child class that will be used to instantiate new items
    CHILD_CLASS: Any = None

    def __init__(self, parents: List[Any]) -> None:
        """
        Args:
            parents: List of parent objects. When creating new children this list will
                be extended to include the current instance and passed along.

        """
        self.parents = parents
        self._items = []

    def __len__(self) -> int:
        """Returns number of items"""
        return len(self._items)

    def __getitem__(self, key: Union[int, slice]) -> Any:
        """Returns a specific item by list index"""
        return self._items[key]

    def __iter__(self) -> Iterator:
        """Returns an iterator of items"""
        return iter(self._items)

    def create(self, *args, **kwargs) -> Any:
        """Factory method for instantiating a new item"""
        parents = self.parents + [self]
        return self.CHILD_CLASS(parents, *args, **kwargs)

    def fetch(self, *args, **kwargs) -> "Collection":
        """Fetch the list of items.

        Child classes must override this method.
        """
        raise NotImplementedError()
