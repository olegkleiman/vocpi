from collections import defaultdict
import asyncio

class SessionPubSub:
    def __init__(self):
        # Maps session_id -> list of subscriber queues
        self._topics: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, session_id: str):
        """Creates a private queue for a client to listen to a specific session."""
        queue = asyncio.Queue()
        self._topics[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """Removes the queue when the client disconnects."""
        if session_id in self._topics:
            self._topics[session_id].remove(queue)
            if not self._topics[session_id]:
                del self._topics[session_id]

    async def publish(self, session_id: str, message: dict):
        """Sends a message to EVERYONE listening to this specific session_id."""
        if session_id in self._topics:
            # We send to all queues associated with this session
            for queue in self._topics[session_id]:
                await queue.put(message)