import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BookingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.booking_id = self.scope["url_route"]["kwargs"]["booking_id"]
        self.room_group_name = f"booking_{self.booking_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def booking_accepted(self, event):
        await self.send(text_data=json.dumps({
            "type": "booking_accepted",
            "booking_id": self.booking_id
        }))



class TrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.booking_id = self.scope["url_route"]["kwargs"]["booking_id"]
        self.room_group_name = f"tracking_{self.booking_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def driver_location_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "driver_location_update",
            "booking_id": self.booking_id,
            "lat": event["lat"],
            "lng": event["lng"],
        }))



async def booking_accepted(self, event):
    await self.send(text_data=json.dumps({
        "type": "booking_accepted",
        "booking_id": event.get("booking_id", self.booking_id),
        "driver_name": event.get("driver_name", ""),
        "contact_number": event.get("contact_number", ""),
        "motorcycle_model": event.get("motorcycle_model", ""),
        "plate_number": event.get("plate_number", ""),
    }))