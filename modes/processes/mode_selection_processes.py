from . import commons
from db.models import HardwareData
from channels.db import database_sync_to_async


async def select_mode_0(hardware_id):
    
    # Get hardware status
    hardware_status = await commons.Get_hardware_status(hardware_id)
    
    # Get remaining amount of pickup task
    remain_pickup_info = await commons.Get_remain_pickup_list(hardware_id)
    pickup_amount = remain_pickup_info['total_pickup'] - remain_pickup_info['done_pickup']
    
    # Get remaining amount of location transfer task
    remain_location_transfer = await commons.Get_remain_location_transfer_list(hardware_id)
    location_transfer_amount = remain_location_transfer['total_location_transfer'] - remain_location_transfer['done_location_transfer']

    # Return webapp payload
    return commons.Payloads.mode_selections(
        new_mode=0,
        hardware_status=hardware_status,
        pickup_amount=pickup_amount,
        location_transfer_amount=location_transfer_amount
    )


async def select_mode_2(hardware_id):

    # Get hardware status
    hardware_status = await commons.Get_hardware_status(hardware_id)

    # Return webapp payload
    return commons.Payloads.mode_selections(
        new_mode=2,
        hardware_status=hardware_status
    )


async def select_mode_3(hardware_id):
    
    # Get hardware status
    hardware_status = await commons.Get_hardware_status(hardware_id)

    # Get data about remaining pickup list
    remain_pickup_info = await commons.Get_remain_pickup_list(hardware_id)

    total_pickup = remain_pickup_info['total_pickup']
    done_pickup = remain_pickup_info['done_pickup']
    data = remain_pickup_info['data']

    # Return webapp payload
    return commons.Payloads.mode_selections(
        new_mode=3,
        hardware_status=hardware_status,
        total_pickup=total_pickup,
        done_pickup=done_pickup,
        data=data
    )


async def select_mode_4(hardware_id):
    
    # Get hardware status
    hardware_status = await commons.Get_hardware_status(hardware_id)

    # Get other location transfer orders of hardwaare for notifying
    remain_location_transfer_orders = await commons.Get_remain_location_transfer_list(hardware_id)

    total_location_transfer = remain_location_transfer_orders['total_location_transfer']
    done_location_transfer = remain_location_transfer_orders['done_location_transfer']
    data = remain_location_transfer_orders['data']

    # Return webapp payload
    return commons.Payloads.mode_selections(
        new_mode=4,
        hardware_status=hardware_status,
        total_location_transfer=total_location_transfer,
        done_location_transfer=done_location_transfer,
        data=data
    )