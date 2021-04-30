import json
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
from db.models import LogData, HardwareData, PalletData, LayoutData, ItemData, PickupData, LocationTransferData, UserData
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import F
import hashlib


''' Constants '''
EMPTY_PALLET_WEIGHT = 5.00
PALLET_WEIGHT_ERROR = 0.1


''' Function for calculating range of expected weight '''
def Range_expected_weight(expected_weight):
    min_weight = (1 - PALLET_WEIGHT_ERROR) * expected_weight
    max_weight = (1 + PALLET_WEIGHT_ERROR) * expected_weight

    return min_weight, max_weight


''' Function for convert datetime from UTC to GMT+7 (local) '''
def Convert_to_local_datetime(UTCdatetime):
    return UTCdatetime + timedelta(hours=7)


''' Function for getting now local datetime as GMT+7 '''
def Get_now_local_datetime():
    return Convert_to_local_datetime(timezone.now())


''' Function for storing log into LOG_DATA '''
async def Store_log(create_log_dict):

    # store log row into LOG_DATA
    await database_sync_to_async(
        lambda : LogData.objects.create(**create_log_dict)
    )()


''' Function for notifying clients by sending payload '''
async def Notify_clients(hardware_id, hardware_payload=None, webapp_payload=None):
    # Define channel layer from outside of consumer class
    channel_layer = get_channel_layer()

    # Process hardware & webapp serial number
    hardware_serial_number = ''.join(('hw', hardware_id))
    webapp_serial_number = ''.join(('sw', hardware_id))

    # Send payload to hardware if it exists
    if hardware_payload is not None:
        await channel_layer.group_send(
            hardware_serial_number,
            {
                "type": "modes.send_payload",
                "payload_string": json.dumps(hardware_payload)
            },
        )

    # Send payload to webapp if it exists
    if webapp_payload is not None:
        await channel_layer.group_send(
            webapp_serial_number,
            {
                "type": "modes.send_payload",
                "payload_string": json.dumps(webapp_payload)
            },
        )


''' Function for updating pallet information in PALLET_DATA '''
async def Update_pallet_info(pallet_id, update_info_dict):
    await database_sync_to_async(
        lambda: PalletData.objects.filter(palletid=pallet_id).update(**update_info_dict)
    )()


''' Function for updating multiple pallets' information in PALLET_DATA '''
async def Update_multiple_pallets_info(pallet_id_list, update_info_dict):
    await database_sync_to_async(
        lambda: PalletData.objects.filter(palletid__in=pallet_id_list).update(**update_info_dict)
    )()


''' Function for updating location information in LAYOUT_DATA '''
async def Update_location_info(location, update_info_dict):
    await database_sync_to_async(
        lambda: LayoutData.objects.filter(location=location).update(**update_info_dict)
    )()


''' Function for getting pallet information in PALLET_DATA '''
async def Get_pallet_info(pallet_id, wanted_fields):
    return await database_sync_to_async(
        lambda: PalletData.objects.filter(palletid=pallet_id).values(*wanted_fields).last()
    )()


''' Function for getting location information in LAYOUT_DATA '''
async def Get_location_info(location, wanted_fields):
    return await database_sync_to_async(
        lambda: LayoutData.objects.filter(location=location).values(*wanted_fields).last()
    )()


''' Function for getting item information in ITEM_DATA '''
async def Get_item_info(item_number, wanted_fields):
    return await database_sync_to_async(
        lambda: ItemData.objects.filter(itemnumber=item_number).values(*wanted_fields).last()
    )()


''' Function for getting pallet information in PALLET_DATA '''
async def Get_multiple_items_info(item_number_list, wanted_fields):
    return await database_sync_to_async(
        lambda: list(ItemData.objects.filter(itemnumber__in=item_number_list).values(*wanted_fields))
    )()


''' Function for getting pickup information in PICKUP_DATA with various filters '''
async def Get_pickup_info_various_filters(filters_dict, wanted_fields):
    return await database_sync_to_async(
        lambda: list(PickupData.objects.filter(**filters_dict).values(*wanted_fields))
    )()


''' Function for updating pickup information in PICKUP_DATA '''
async def Update_pickup_info(pickup_id, update_info_dict):
    await database_sync_to_async(
        lambda: PickupData.objects.filter(pickupid=pickup_id).update(**update_info_dict)
    )()


''' Function for notifying order to webapp for picking up that day '''
async def Notify_pickup(hardware_id):
    payload_info = await Get_remain_pickup_list(hardware_id)

    # Generate payload for sending to webapp
    webapp_payload = Payloads.m3s0(
        total_pickup=payload_info['total_pickup'],
        done_pickup=payload_info['done_pickup'],
        data=payload_info['data']
    )

    # Send payload to webapp
    await Notify_clients(
        hardware_id=hardware_id,
        webapp_payload=webapp_payload
    )


''' Function for getting remaining pickup list for picking up of specific hardware '''
async def Get_remain_pickup_list(hardware_id):
    # Initialize data for sending to considered hardware ID with webapp payload
    data = []

    # Get pickup information of wanted records for sending to webapp, which have to be picked up today
    pickup_info = await database_sync_to_async(
        lambda: list(
                    PickupData.objects.filter(
                        orderlistid__ordernumber__duedate=Get_now_local_datetime().date(),
                        hardwareid=hardware_id
                    ).annotate(
                        order_number=F('orderlistid__ordernumber'),
                        item_name=F('palletid__itemnumber__itemname'),
                        location=F('palletid__location')
                    ).order_by('pickupid').values('order_number', 'pickupid', 'palletid', 'item_name', 'location', 'pickupstatus')
                )
    )()

    # Get total pickup amount for today
    total_pickup = len(pickup_info)

    # Update data header
    for pickup in pickup_info:
        if pickup['pickupstatus'] == 'WAITPICK':
            data.append({
                'order_number': pickup['order_number'],
                'pickup_id': pickup['pickupid'],
                'pickup_type': 'full',
                'pallet_id': pickup['palletid'],
                'item_name': pickup['item_name'],
                'location': pickup['location']
            })

    return {
        'total_pickup': total_pickup,
        'done_pickup': total_pickup - len(data),
        'data': data
    }


''' Function for getting remaining location transfer list for moving of specific hardware '''
async def Get_remain_location_transfer_list(hardware_id):
    
    # Initialize data for sending to considered hardware ID with webapp payload
    data = []
    
    # Get location transfer information of wanted orders for sending to webapp, which have to be moved today
    location_transfer_orders = await database_sync_to_async(
        lambda: list(
            LocationTransferData.objects.filter(
                registertimestamp__date=Get_now_local_datetime().date(),
                hardwareid=hardware_id
            ).order_by('locationtransferid').values('sourcelocation', 'destinationlocation', 'locationtransferstatus')
        )
    )()

    # Get the number of total location transfer orders for today
    total_location_transfer = len(location_transfer_orders)

    # Update data header
    for location_transfer_order in location_transfer_orders:
        if location_transfer_order['locationtransferstatus'] == 'WAITMOVE':
            data.append({
                'source': location_transfer_order['sourcelocation'],
                'destination': location_transfer_order['destinationlocation']
            })

    return {
        'total_location_transfer': total_location_transfer,
        'done_location_transfer': total_location_transfer - len(data),
        'data': data
    }


''' Function for updating mode in HARDWARE_DATA '''
async def Update_current_mode_stage(hardware_id, mode, stage):
    await database_sync_to_async(
        lambda: HardwareData.objects.filter(hardwareid=hardware_id, isactive=True).update(currentmode=mode, currentstage=stage)
    )()

    await database_sync_to_async(
        lambda: UserData.objects.filter(hardwareid=hardware_id).update(currentmode=mode, currentstage=stage)
    )()


''' Function for handling simple pallet rejection '''
async def Handle_pallet_rejection(pallet_id, location):

    await Update_pallet_info(
        pallet_id=pallet_id,
        update_info_dict={'palletstatus': 'REJECT', 'location': None}
    )

    await Update_location_info(
        location=location,
        update_info_dict={'locationstatus': 'BLANK'}
    )


''' Function for handling pallet rejection when wanted location stored unwanted pallet '''
async def Pallet_rejection_of_pallet_in_wrong_location(unwanted_pallet_id, wanted_pallet_id, wanted_location):
    
    # 4
    location_of_unwanted_pallet = (
        await Get_pallet_info(
            pallet_id=unwanted_pallet_id,
            wanted_fields=('location',)
        )
    )['location']

    await Update_location_info(
        location=location_of_unwanted_pallet,
        update_info_dict={'locationstatus': 'CHECK'}
    )

    # 1 & 3
    await Handle_pallet_rejection(
        pallet_id=unwanted_pallet_id,
        location=wanted_location
    )

    # 2
    await Update_pallet_info(
        pallet_id=wanted_pallet_id,
        update_info_dict={'palletstatus': 'WRONGLOC', 'location': None}
    )


''' Function for handling pallet rejection when pallet has wrong amount '''
async def Pallet_rejection_of_pallet_amount(scanned_pallet_id):

    location = (
        await Get_pallet_info(
            pallet_id=scanned_pallet_id,
            wanted_fields=('location',)
        )
    )['location']

    await Handle_pallet_rejection(
        pallet_id=scanned_pallet_id,
        location=location
    )


''' Function for getting hardware status of specific hardware ID '''
async def Get_hardware_status(hardware_id):
    return await database_sync_to_async(
        lambda: HardwareData.objects.filter(hardwareid=hardware_id).values_list('isactive', flat=True).first()
    )()


''' Function for getting hashed ticket '''
def Get_hashed_ticket(unhashed_ticket):
    return hashlib.sha256(unhashed_ticket.encode()).hexdigest()


''' Class for generating payloads in every modes and stages '''
class Payloads():

    # Mode 2 Stage 1
    def m2s1( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 1,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 2,
            "stage": 1,
            "is_notify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "data": kwargs['data']
        }

        return hw, sw

    # Mode 2 Stage 2
    def m2s2( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 2,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 2,
            "stage": 2,
            "is_notify": True,
            "status": kwargs['status'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 2 Stage 3
    def m2s3( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 3,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 2,
            "stage": 3,
            "is_notify": True,
            "status": kwargs['status'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 3 Stage 1
    def m3s1( **kwargs ):
        sw = {
            'mode': 3,
            'stage': 1,
            'is_notify': True
        }

        return sw

    # Mode 3 Stage 2
    def m3s2( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 3,
            "stage": 2,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 3,
            "stage": 2,
            "is_notify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 3 Stage 3
    def m3s3( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 3,
            "stage": 3,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 3,
            "stage": 3,
            "is_notify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type']
        }

        return hw, sw

    # Mode 3 Stage 4
    def m3s4( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 3,
            "stage": 4,
            "status": True,
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 3,
            "stage": 4,
            "is_notify": True,
            "status": True,
            "total_pickup": kwargs['total_pickup'],
            "done_pickup": kwargs['done_pickup'],
            "data": kwargs['data']
        }

        return hw, sw

    # Mode 4 Stage 1
    def m4s1():
        sw = {
            "mode": 4,
            "stage": 1,
            "is_notify": True,
        }

        return sw

    # Mode 4 Stage 2
    def m4s2( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 4,
            "stage": 2,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 4,
            "stage": 2,
            "is_notify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 4 Stage 3
    def m4s3( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 4,
            "stage": 3,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw = {
            "mode": 4,
            "stage": 3,
            "is_notify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 4 Stage 4
    def m4s4( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 4,
            "stage": 4,
            "status": kwargs['status'],
            "new_mode": kwargs['new_mode'],
            "new_stage": kwargs['new_stage']
        }

        sw =    {
            "mode": 4,
            "stage": 4,
            "is_notify": True,
            "status": kwargs['status'],
            "current_location": kwargs['scanned_location'],
            "total_location_transfer": kwargs['total_location_transfer'],
            "done_location_transfer": kwargs['done_location_transfer'], 
            "data": kwargs['data']
        }

        return hw, sw

    # Mode selection payload for webapp
    def mode_selections(new_mode, **kwargs ):
        
        if new_mode == 0:
            return {
                "mode": 0,
                "stage": 0,
                "hardware_status": kwargs['hardware_status'],
                "pickup_amount": kwargs['pickup_amount'],
                "location_transfer_amount": kwargs['location_transfer_amount']
            }

        elif new_mode == 2:
            return {
                "mode": 2,
                "stage": 0,
                "is_notify": False,
                "hardware_status": kwargs['hardware_status']
            }

        elif new_mode == 3:
            return {
                "mode": 3,
                "stage": 0,
                "is_notify": False,
                "hardware_status": kwargs['hardware_status'],
                "total_pickup": kwargs['total_pickup'],
                "done_pickup": kwargs['done_pickup'],
                "data": kwargs['data']
            }

        elif new_mode == 4:
            return {
                "mode": 4,
                "stage": 0,
                "is_notify": False,
                "hardware_status": kwargs['hardware_status'],
                "total_location_transfer": kwargs['total_location_transfer'],
                "done_location_transfer": kwargs['done_location_transfer'], 
                "data": kwargs['data']
            }

        else:
            return None

    # Mode 5 (connect / disconnect)
    def m5_to_hardware(status, employee_id=None):
        return {
            "mode": 5,
            "employee_id": employee_id,
            "webapp_status": status
        }

    def m5_to_webapp(status):
        return {
            "mode": 5,
            "hardware_status": status
        }

    # Mode changed
    def mode_changed_to_hardware(new_mode, new_stage):
        return {
            "information_type": 'mode_changed',
            "new_mode": new_mode,
            "new_stage": new_stage
        }
