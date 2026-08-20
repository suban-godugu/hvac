"""
PlantControlRealtimeService: Manages realtime streaming, pub/sub subscribers,
and broadcast events for Plant Control Parameter Optimizations.
"""
from typing import Dict, Any, List, Callable
import asyncio
import json
from datetime import datetime, timezone

class PlantControlRealtimeService:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        """Subscribes an SSE or WebSocket client queue to plant control live events."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Unsubscribes a client queue."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast_event(self, event_type: str, opportunity: str, data: Dict[str, Any]):
        """Broadcasts an event payload to all active client queues."""
        payload = {
            "event": event_type,
            "opportunity": opportunity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for d in dead:
            self.unsubscribe(d)

    def get_realtime_status(self) -> Dict[str, Any]:
        return {
            "active_subscribers": len(self._subscribers),
            "streaming_active": True,
            "protocol": "SSE/WebSocket",
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }

plant_control_realtime_service = PlantControlRealtimeService()
