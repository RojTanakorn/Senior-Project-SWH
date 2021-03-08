  
from channels.generic.websocket import AsyncWebsocketConsumer
from .processes.operate import Operate


class ModeConsumer(AsyncWebsocketConsumer):
    ''' Called when client want to connect with Websocket '''
    async def connect(self):
        # Get serial number of client from url path
        self.its_serial_number = self.scope['url_route']['kwargs']['serial_number']

        # Create group channel of client (each group contains only 1 client)
        await self.channel_layer.group_add(
            self.its_serial_number,
            self.channel_name
        )

        # Accept this connection
        await self.accept()


    ''' Called when client want to disconnect '''
    async def disconnect(self, close_code):
        # Leave a group
        await self.channel_layer.group_discard(
            self.its_serial_number,
            self.channel_name
        )


    ''' Called when receive data from WebSocket '''
    async def receive(self, text_data):
        # Process payload in Operate function
        await Operate(self.its_serial_number, text_data)


    ''' Called when the mode want to send payload '''
    async def modes_send_payload(self, event):
        # Get payload string for sending to client
        payload_string = event['payload_string']

        # Send payload using WebSocket to client
        await self.send(text_data=payload_string)