from collections import defaultdict
import asyncio

class OCPIPubSub:
    def __init__(self):
        # Maps topic_id -> list of subscriber queues
        self._topics: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, topic_id: str):
        """Creates a private queue for a client to listen to a specific topic."""
        queue = asyncio.Queue(maxsize=100)
        self._topics[topic_id].append(queue)
        return queue

    def unsubscribe(self, topic_id: str, queue: asyncio.Queue):
        """Removes the queue when the client disconnects."""
        if topic_id in self._topics:
            self._topics[topic_id].remove(queue)
            if not self._topics[topic_id]:
                del self._topics[topic_id]

    async def publish(self, topic_id: str, message: dict):
        """Sends a message to EVERYONE listening to this specific topic_id."""
        if topic_id in self._topics:
            # We send to all queues associated with this topic
            for queue in self._topics[topic_id]:
                await queue.put_nowait(message)