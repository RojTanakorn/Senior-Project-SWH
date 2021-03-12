import json
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
from db.models import LogData, HardwareData, PalletData, LayoutData
from channels.db import database_sync_to_async
from django.utils import timezone


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
        lambda : 
            LogData.objects.create(**create_log_dict)
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