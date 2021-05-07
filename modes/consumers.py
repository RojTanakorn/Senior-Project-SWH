from channels.generic.websocket import AsyncWebsocketConsumer
from .processes.operate import Operate, Mode_selection_management
from django.core.cache import cache
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from db.models import HardwareData, UserData
from .processes import commons, mode_selection_processes


class ModeConsumer(AsyncWebsocketConsumer):

    ''' Called when client want to connect with Websocket '''
    async def connect(self):

        print('\n\n================ CONNECT PROCESS ==================')

        # Get serial number a shas_ticket status of client from url path
        self.its_serial_number = self.scope['url_route']['kwargs']['serial_number']
        self.client_type = self.its_serial_number[:2]
        self.hardware_id = self.its_serial_number[2:]

        # If hardware is connecting
        if self.client_type == 'hw':

            # Check existing hardware ID in HARDWARE_DATA
            # If hardware ID exists:    - accept this connection
            #                           - update active status of hardware to be TRUE
            #                           - check optional process.
            # Else, reject connection
            hardware_object = await database_sync_to_async(
                lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).first()
            )()

            if hardware_object is not None:
                print('hw[1/1] hw valid: PASS')

                await database_sync_to_async(
                    lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(isactive=True)
                )()

                await self.channel_layer.group_add(
                    self.its_serial_number,
                    self.channel_name
                )
                await self.accept()

                # Check optional process:
                # - user already bind this hardware or not
                #       - If true:
                #           - send mode_changed payload to hardware as current mode-stage (Hardware can continue task defined by an employee)
                #           - send hardware status to webapp (True)
                #           - send webapp status to hardware with status=True and employee ID
                #           - update current mode-stage as same as webapp task
                #       - If false
                #           - send mode_changed payload to hardware as mode 0 stage 0
                #           - send webapp status to hardware with status=False
                user_object = await database_sync_to_async(
                    lambda: UserData.objects.filter(hardwareid=self.hardware_id, ison=True).values().first()
                )()

                hardware_payload, webapp_payload = None, None
                employee_id = None
                is_on = False

                if user_object is None:
                    print('hw[optional] user binded: FALSE')
                    hardware_payload = commons.Payloads.mode_changed_to_hardware(0, 0)

                else:
                    print('hw[optional] user binded: TRUE')
                    employee_id = user_object['userid_id']
                    is_on = True

                    await database_sync_to_async(
                        lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                            currentmode=user_object['currentmode_id'], currentstage=user_object['currentstage']
                        )
                    )()

                    hardware_payload = commons.Payloads.mode_changed_to_hardware(user_object['currentmode_id'], user_object['currentstage'])
                    webapp_payload = commons.Payloads.m5_to_webapp(True)

                await commons.Notify_clients(
                    self.hardware_id,
                    hardware_payload=commons.Payloads.m5_to_hardware(is_on, employee_id)
                )

                await commons.Notify_clients(self.hardware_id, hardware_payload, webapp_payload)

            # Hardware ID does not exist
            else:
                await self.accept()
                await self.close(code=4444)

        # If webapp is connecting
        elif self.client_type == 'sw':
            
            # Get has_ticket status from url and initialize is_accept status
            has_ticket = self.scope['url_route']['kwargs']['has_ticket']
            is_accept = False

            # Checking process:
            #       1. client send a ticket or not
            #       2. ticket of client IP has expired or not
            #       3. ticket is valid or not
            #       4. hardware ID exists or not
            #       5. hardware ID is already binded to another user or not
            # If all checklist passed, accpect connection, update data, and send payload to hardware and webapp if need
            
            # Checklist 1:
            if has_ticket:
                print('sw[1/5] has ticket: PASS')
                cache_result = await sync_to_async(cache.get)(self.scope['client'][0])
                user_unhashed_ticket = self.scope['url_route']['kwargs']['unhashed_ticket']

                # Checklist 2:
                if cache_result is not None:
                    print('sw[2/5] ticket not none: PASS')
                    user_hashed_ticket = commons.Get_hashed_ticket(user_unhashed_ticket)
                    cache_hashed_ticket = cache_result['hashed_ticket']

                    # Checklist 3:
                    if user_hashed_ticket == cache_hashed_ticket:
                        print('sw[3/5] check ticket: PASS')
                        hardware_object = await database_sync_to_async(
                            lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).first()
                        )()
                        
                        # Checklist 4:
                        if hardware_object is not None:
                            print('sw[4/5] hw valid: PASS')
                            user_object = await database_sync_to_async(
                                lambda: UserData.objects.filter(hardwareid=self.hardware_id, ison=True).first()
                            )()
                            
                            # Checklist 5:
                            if user_object is None:
                                print('sw[5/5] hw binded: PASS')

                                # ===== PASSED ALL CHECKLISTS =====
                                # Allow server to accept
                                is_accept = True
                                
                                # Update is_on status of user and bind hardware ID
                                await database_sync_to_async(
                                    lambda: UserData.objects.filter(userid=cache_result['user_id']).update(ison=True, hardwareid_id=self.hardware_id)
                                )()

                                # Create layer and accept this connection
                                await self.channel_layer.group_add(
                                    self.its_serial_number,
                                    self.channel_name
                                )
                                await self.accept()

                                # Check hardware ID is active or not.
                                # If it is active, send webapp status (mode 5) to hardware
                                if hardware_object.isactive == True:
                                    print('sw[optional] hw active: TRUE')
                                    await commons.Notify_clients(self.hardware_id, commons.Payloads.m5_to_hardware(True, cache_result['user_id']))
                                
                                # Get user object and send current mode-stage
                                # Then, send mode_changed to hardware according to webapp, and update mode-stage of hardware
                                user_object = await database_sync_to_async(
                                    lambda: UserData.objects.filter(userid=cache_result['user_id']).first()
                                )()

                                await database_sync_to_async(
                                    lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                                        currentmode=user_object.currentmode_id, currentstage=user_object.currentstage
                                    )
                                )()

                                # If mode 0 stage 0, send as mode_selection
                                if user_object.currentmode_id == 0 and user_object.currentstage == 0:
                                    webapp_payload = await mode_selection_processes.select_mode_0(self.hardware_id)
                                
                                else:
                                    # Send payload about hardware status to webapp
                                    webapp_payload = commons.Payloads.m5_to_webapp(hardware_object.isactive)

                                # Send payload about current mode-stage to hardware
                                hardware_payload = commons.Payloads.mode_changed_to_hardware(user_object.currentmode_id, user_object.currentstage)
                                await commons.Notify_clients(self.hardware_id, hardware_payload, webapp_payload)

            if not is_accept:
                print('not accept')
                await self.accept()
                await self.close(code=4444)
        
        # Not hardware and webapp standard connection
        else:
            await self.accept()
            await self.close(code=4444)


    ''' Called when client want to disconnect '''
    async def disconnect(self, close_code):

        print('\n\n=============== DISCONNECT PROCESS ================')
        print('close code:', close_code)

        hardware_payload, webapp_payload = None, None

        # If hardware disconnected
        #   - reset mode-stage to 0
        #   - active status = False
        #   - send hardware status to webapp
        if self.client_type == 'hw':

            await database_sync_to_async(
                lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                    currentmode=0,
                    currentstage=0,
                    isactive=False
                )
            )()

            webapp_payload = commons.Payloads.m5_to_webapp(False)
        
        # If webapp disconnected
        elif self.client_type == 'sw':
            
            # If disconnect that user logout or close browser
            #   - Send mode_changed payload to hardware as mode 0 stage 0 (hardware stops working)
            #   - Update is_on = False, and unbind hardware
            #   - Update current mode-stage of hardware to be 0
            #   - Send webapp status to hardware which webapp status=False, unbinded employee ID
            if close_code in [None, 1001, 1006]:

                await commons.Notify_clients(hardware_id=self.hardware_id, hardware_payload=commons.Payloads.mode_changed_to_hardware(0, 0))
                
                updating_user_dict = {'ison': False, 'hardwareid_id': None}

                if close_code != 1006:
                    updating_user_dict.update({'currentmode': 0, 'currentstage': 0})

                await database_sync_to_async(
                    lambda: UserData.objects.filter(hardwareid=self.hardware_id).update(**updating_user_dict)
                )()

                await database_sync_to_async(
                    lambda: HardwareData.objects.filter(hardwareid=self.hardware_id).update(
                        currentmode=0,
                        currentstage=0
                    )
                )()

                hardware_payload = commons.Payloads.m5_to_hardware(False, None)

        # Send payload to another client (paired)
        await commons.Notify_clients(self.hardware_id, hardware_payload, webapp_payload)

        # Leave a group
        await self.channel_layer.group_discard(
            self.its_serial_number,
            self.channel_name
        )


    ''' Called when receive data from WebSocket '''
    async def receive(self, text_data):

        # Process hardware payload in Operate function
        if self.client_type == 'hw':
            await Operate(self.hardware_id, text_data)

        # Process mode selection of webapp in Mode_selection_management function
        elif self.client_type == 'sw':
            await Mode_selection_management(self.hardware_id, text_data)


    ''' Called when the mode want to send payload '''
    async def modes_send_payload(self, event):
        
        # Get payload string for sending to client
        payload_string = event['payload_string']

        # Send payload using WebSocket to client
        await self.send(text_data=payload_string)