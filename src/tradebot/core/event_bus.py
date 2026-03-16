"""Central event bus with type-based dispatch and observer pattern."""
import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

class EventBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._handlers: dict[type, Callable[..., Coroutine[Any, Any, list]]] = {}
        self._observers: list[Callable[..., Coroutine[Any, Any, None]]] = []

    def register_handler(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def add_observer(self, observer: Callable) -> None:
        self._observers.append(observer)

    async def publish(self, event: Any) -> None:
        await self._queue.put(event)

    async def process_one(self) -> bool:
        try:
            event = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return False
        for observer in self._observers:
            await observer(event)
        handler = self._handlers.get(type(event))
        if handler:
            new_events = await handler(event)
            for e in new_events or []:
                await self._queue.put(e)
        return True

    async def run(self, shutdown_event: asyncio.Event | None = None) -> None:
        while True:
            if shutdown_event and shutdown_event.is_set():
                break
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            for observer in self._observers:
                await observer(event)
            handler = self._handlers.get(type(event))
            if handler:
                new_events = await handler(event)
                for e in new_events or []:
                    await self._queue.put(e)

    @property
    def pending(self) -> int:
        return self._queue.qsize()
