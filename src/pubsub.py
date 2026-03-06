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
        if topic_id not in self._topics:
            return

        # We iterate over a copy to prevent "Set changed size during iteration" errors
        # if someone unsubscribes while we are publishing.
        for queue in list(self._topics[topic_id]):
            try:
                queue.put_nowait(message) 
            except asyncio.QueueFull:
                # If a client is too slow, we drop the message for them
                # or you could unsubscribe them automatically here.
                pass