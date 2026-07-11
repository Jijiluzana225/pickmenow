
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class BookingConsumer(AsyncWebsocketConsumer):
    """
    Used by the customer booking page.

    Group name:
        booking_<booking_id>
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.booking_id = self.scope["url_route"]["kwargs"]["booking_id"]
        self.room_group_name = f"booking_{self.booking_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def booking_accepted(self, event):
        """
        Handles messages with:

        {
            "type": "booking_accepted",
            ...
        }
        """

        await self.send(
            text_data=json.dumps({
                "type": "booking_accepted",
                "booking_id": event.get(
                    "booking_id",
                    self.booking_id
                ),
                "driver_name": event.get(
                    "driver_name",
                    ""
                ),
                "contact_number": event.get(
                    "contact_number",
                    ""
                ),
                "motorcycle_model": event.get(
                    "motorcycle_model",
                    ""
                ),
                "plate_number": event.get(
                    "plate_number",
                    ""
                ),
            })
        )


class TrackingConsumer(AsyncWebsocketConsumer):
    """
    Used by the customer tracking page.

    Group name:
        tracking_<booking_id>
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.booking_id = self.scope["url_route"]["kwargs"]["booking_id"]
        self.room_group_name = f"tracking_{self.booking_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def driver_location_update(self, event):
        """
        Handles messages with:

        {
            "type": "driver_location_update",
            "lat": ...,
            "lng": ...
        }
        """

        await self.send(
            text_data=json.dumps({
                "type": "driver_location_update",
                "booking_id": event.get(
                    "booking_id",
                    self.booking_id
                ),
                "lat": event.get("lat"),
                "lng": event.get("lng"),
            })
        )

    async def booking_accepted(self, event):
        """
        Optional handler for the tracking page when a driver accepts.
        """

        await self.send(
            text_data=json.dumps({
                "type": "booking_accepted",
                "booking_id": event.get(
                    "booking_id",
                    self.booking_id
                ),
                "driver_name": event.get(
                    "driver_name",
                    ""
                ),
                "contact_number": event.get(
                    "contact_number",
                    ""
                ),
                "motorcycle_model": event.get(
                    "motorcycle_model",
                    ""
                ),
                "plate_number": event.get(
                    "plate_number",
                    ""
                ),
            })
        )


class DriverDashboardConsumer(AsyncWebsocketConsumer):
    """
    Used to refresh all connected driver dashboards belonging
    to the same service location.

    Group name:
        driver_dashboard_location_<location_id>
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        try:
            driver = await self.get_driver_profile(user)
        except Exception:
            await self.close()
            return

        if not driver:
            await self.close()
            return

        if not driver.location_id:
            await self.close()
            return

        if not driver.is_approved:
            await self.close()
            return

        self.location_id = driver.location_id

        self.room_group_name = (
            f"driver_dashboard_location_{self.location_id}"
        )

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def dashboard_refresh(self, event):
        await self.send(
            text_data=json.dumps({
                "type": "dashboard_refresh",
                "booking_id": event.get("booking_id"),
                "booking_status": event.get("booking_status"),
                "reason": event.get("reason"),
            })
        )

    @staticmethod
    async def get_driver_profile(user):
        """
        Access the related DriverProfile safely from an async consumer.
        """

        from channels.db import database_sync_to_async

        @database_sync_to_async
        def fetch_driver():
            try:
                return user.driver_profile
            except Exception:
                return None

        return await fetch_driver()

