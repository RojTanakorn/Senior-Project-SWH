  
from channels.generic.websocket import AsyncWebsocketConsumer
from .processes.operate import Operate, Mode_selection_management
from django.core.cache import cache
from channels.db import database_sync_to_async
from db.models import HardwareData
from .processes import commons


class ModeConsumer(AsyncWebsocketConsumer):
    ''' Called when client want to connect with Websocket '''
    async def connect(self):

        # Get serial number and shas_ticket status of client from url path
        self.its_serial_number = self.scope['url_route']['kwargs']['serial_number']
        self.client_type = self.its_serial_number[:2]
        self.hardware_id = self.its_serial_number[2:]

        if self.client_type == 'hw':

            # Check existing harddware ID in HARDWARE_DATA
            hardware_object = await database_sync_to_async(
                lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).first()
            )()

            # Hardware ID is invalid
            if hardware_object is None:
                await self.close()

            # Hardware ID is valid
            else:
                await database_sync_to_async(
                    lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(isactive=True)
                )()

                await self.channel_layer.group_add(
                    self.its_serial_number,
                    self.channel_name
                )

                # Accept this connection
                await self.accept()

            # Create group channel of client (each group contains only 1 client)
            # await self.channel_layer.group_add(
            #     self.its_serial_number,
            #     self.channel_name
            # )

            # # Accept this connection
            # await self.accept()


        # elif client_type == 'sw':
        #     pass
            # has_ticket = self.scope['url_route']['kwargs']['has_ticket']

            # if has_ticket:
                

            # else:
            #     pass # reject connection --> webapp does not send the ticket

        # else:
            
        #     # reject connection --> it does not specify a type of client
        #     self.close()
        
        # has_ticket = self.scope['url_route']['kwargs']['has_ticket']
        
        

        # if has_ticket:
        #     print('ticket:', self.scope['url_route']['kwargs']['ticket'])
        
        # print(self.scope['client'][0])

        # Create group channel of client (each group contains only 1 client)
        # await self.channel_layer.group_add(
        #     self.its_serial_number,
        #     self.channel_name
        # )

        # # Accept this connection
        # await self.accept()

        


    ''' Called when client want to disconnect '''
    async def disconnect(self, close_code):

        hardware_payload, webapp_payload = None, None

        # If hardware disconnects
        if self.client_type == 'hw':

            await database_sync_to_async(
                lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                    currentmode=0,
                    currentstage=0,
                    isactive=False
                )
            )()

            webapp_payload = commons.Payloads.m5_to_webapp(False)
        
        elif self.client_type == 'sw':
            await database_sync_to_async(
                lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                    currentmode=0,
                    currentstage=0,
                    employeeid=None
                )
            )()

            hardware_payload = commons.Payloads.m5_to_hardware(False)

        # Send payload to another client (paired)
        commons.Notify_clients(self.hardware_id, hardware_payload, webapp_payload)

        # Leave a group
        await self.channel_layer.group_discard(
            self.its_serial_number,
            self.channel_name
        )


    ''' Called when receive data from WebSocket '''
    async def receive(self, text_data):
        
        its_serial_number = self.its_serial_number

        # Process hardware payload in Operate function
        if self.client_type == 'hw':
            await Operate(self.its_serial_number, text_data)

        # Process mode selection of webapp in Mode_selection_management function
        elif self.client_type == 'sw':
            await Mode_selection_management(self.its_serial_number, text_data)


    ''' Called when the mode want to send payload '''
    async def modes_send_payload(self, event):
        # Get payload string for sending to client
        payload_string = event['payload_string']

        # Send payload using WebSocket to client
        await self.send(text_data=payload_string)