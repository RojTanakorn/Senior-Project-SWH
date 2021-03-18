import json
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
from db.models import LogData, HardwareData, PalletData, LayoutData, ItemData, PickupData
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import F


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


''' Function for getting pallet information in PALLET_DATA '''
async def Get_multiple_items_info(item_number_list, wanted_fields):
    return await database_sync_to_async(
        lambda: list(ItemData.objects.filter(itemnumber__in=item_number_list).values(*wanted_fields))
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

    # Get total pickip amount for today
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


''' Class for generating payloads in every modes and stages '''
class Payloads():

    # Mode 2 Stage 0
    def m2s0( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 0,
            "status": kwargs['status'],
            "new_mode": 2,
            "new_stage": 1
        }

        sw = {
            "mode": 2,
            "stage": 0,
            "isNotify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "data": kwargs['data']
        }

        return hw, sw

    # Mode 2 Stage 1
    def m2s1( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 1,
            "status": kwargs['status']
        }

        sw = {
            "mode": 2,
            "stage": 1,
            "isNotify": True,
            "status": kwargs['status'],
            "current_location": kwargs['scanned_location']
        }

        return hw, sw

    # Mode 2 Stage 2
    def m2s2( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 2,
            "stage": 2,
            "status": True
        }

        sw = {
            "mode": 2,
            "stage": 2,
            "isNotify": True,
            "status": kwargs['status']
        }

        return hw, sw

    # Mode 3 Stage 0
    def m3s0( **kwargs ):
        sw = {
            'mode': 3,
            'stage': 0,
            'isNotify': False,
            'total_pickup': kwargs['total_pickup'],
            'done_pickup': kwargs['done_pickup'],
            'data': kwargs['data']
        }

        return sw

    # Mode 3 Stage 1
    def m3s1( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 3,
            "stage": 1,
            "status": kwargs['status'],
            "new_mode": 3,
            "new_stage": 2
        }

        sw = {
            "mode": 3,
            "stage": 1,
            "isNotify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "current_location": kwargs['current_location']
        }

        return hw, sw

    # Mode 3 Stage 2
    def m3s2( **kwargs ):
        hw = {
            "information_type": 'mode',
            "mode": 3,
            "stage": 2,
            "status": kwargs['status'],
            "new_mode": 3 if kwargs['data'] else 0 ,
            "new_stage": 1 if kwargs['data'] else 0
        }

        sw = {
            "mode": 3,
            "stage": 2,
            "isNotify": True,
            "status": kwargs['status'],
            "error_type": kwargs['error_type'],
            "total_pickup": kwargs['total_pickup'],
            "done_pickup": kwargs['done_pickup'],
            "data": kwargs['data']
        }

        return hw, sw
