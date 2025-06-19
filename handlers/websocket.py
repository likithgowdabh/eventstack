import tornado.websocket
import json
from models.db import get_votes_by_event

class VoteWebSocketHandler(tornado.websocket.WebSocketHandler):
    clients = {}  # event_id -> set of websocket connections
    
    def open(self, event_id):
        self.event_id = event_id
        if event_id not in self.clients:
            self.clients[event_id] = set()
        self.clients[event_id].add(self)
        print(f"WebSocket opened for event {event_id}")
    
    def on_close(self):
        if self.event_id in self.clients:
            self.clients[self.event_id].discard(self)
            if not self.clients[self.event_id]:
                del self.clients[self.event_id]
        print(f"WebSocket closed for event {self.event_id}")
    
    def on_message(self, message):
        # Handle incoming messages if needed
        pass
    
    @classmethod
    def broadcast_vote_update(cls, event_id):
        """Broadcast vote updates to all clients watching this event"""
        if event_id not in cls.clients:
            return
        
        # Get current vote counts
        votes = get_votes_by_event(event_id)
        votes_by_slot = {}
        
        for vote in votes:
            slot_id = vote["time_slot_id"]
            if slot_id not in votes_by_slot:
                votes_by_slot[slot_id] = []
            votes_by_slot[slot_id].append({
                "username": vote["username"],
                "avatar_url": vote["avatar_url"]
            })
        
        message = {
            "type": "vote_update",
            "votes_by_slot": votes_by_slot
        }
        
        # Send to all connected clients for this event
        for client in cls.clients[event_id].copy():
            try:
                client.write_message(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to client: {e}")
                cls.clients[event_id].discard(client)
    
    def check_origin(self, origin):
        return True  # Allow all origins for now
