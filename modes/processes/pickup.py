from channels.db import database_sync_to_async
from . import commons
from django.db.models import F, Sum
from db.models import PickupData, PalletData, OrderData, OrderListData


''' **************************************************** '''
''' **************** MAIN FUNCTION PART **************** '''
''' **************************************************** '''

''' Function for processing pickup mode '''
async def Pickup_mode(its_serial_number, payload_json, current_mode, current_stage):
    
    # Get only hardware ID's sender and employee ID
    hardware_id = its_serial_number[2:]
    employee_id = payload_json['employee_id']

    # Process data in stage 0
    if current_stage == 1:
        await Pickup_stage_1(hardware_id, employee_id, payload_json)

    # Process data in stage 1
    elif current_stage == 2:
        await Pickup_stage_2(hardware_id, employee_id, payload_json)

    
''' ****************************************************** '''
''' **************** STAGE FUNCTIONS PART **************** '''
''' ****************************************************** '''

''' Function stage 1 '''
async def Pickup_stage_1(hardware_id, employee_id, payload_json):
    
    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    verify_pickup_pallet_status, error_type = await Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id)

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if verify_pickup_pallet_status else 'ERR',
            'errorfield': error_type,
            'mode_id': 3,
            'stage': 1,
            'scanpallet': scanned_pallet_id,
            'scanlocation': scanned_location,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m3s1(
        status=verify_pickup_pallet_status,
        error_type=error_type,
        current_location=scanned_location
    )

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )



''' Function stage 2 '''
async def Pickup_stage_2(hardware_id, employee_id, payload_json):
    
    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_pallet_weight = payload_json['pallet_weight']

    verify_pickup_amount_status, error_type, order_info = await Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id)

    total_pickup = None
    done_pickup = None
    data = None

    if verify_pickup_amount_status:
        # update
        # 1. pallet status -> PICKED
        # 2. check this order number is picked up completely? -> complete - PICKED, not - PICKING
        # 3. remain pickup quantity
        # 4. pickup status -> PICKED

        await database_sync_to_async(
            lambda: PalletData.objects.filter(palletid=scanned_pallet_id).update(palletstatus='PICKED')
        )()

        await database_sync_to_async(
            lambda: OrderListData.objects.filter(orderlistid=order_info['order_list_id']).update(
                remainpickupquantity=F('remainpickupquantity') - order_info['pick_quantity']
            )
        )()

        await database_sync_to_async(
            lambda: PickupData.objects.filter(pickupid=order_info['pickup_id']).update(pickupstatus='PICKED')
        )()

        remain_pickup_quantity_sum = await database_sync_to_async(
            lambda: OrderListData.objects.filter(
                ordernumber=order_info['order_number']
            ).aggregate(Sum('remainpickupquantity'))['remainpickupquantity__sum']
        )()

        if bool(remain_pickup_quantity_sum):
            order_status = 'PICKING'
        else:
            order_status = 'PICKED'
            
        await database_sync_to_async(
            lambda: OrderData.objects.filter(ordernumber=order_info['order_number']).update(orderstatus=order_status)
        )()

        # send new data for picking
        remain_pickup_info = await commons.Get_remain_pickup_list(hardware_id)

        total_pickup = remain_pickup_info['total_pickup']
        done_pickup = remain_pickup_info['done_pickup']
        data = remain_pickup_info['data']

    # else:

    #     # data is None
    #     data = None

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if verify_pickup_amount_status else 'ERR',
            'errorfield': error_type,
            'mode_id': 3,
            'stage': 2,
            'scanpallet': scanned_pallet_id,
            'scanpalletweight': scanned_pallet_weight,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m3s2(
        status=verify_pickup_amount_status,
        error_type=error_type,
        total_pickup=total_pickup,
        done_pickup=done_pickup,
        data=data
    )

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

async def Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id):

    # Initialize status and error type
    verify_pickup_pallet_status = False
    error_type = None

    # Check that employee go to correct pallet & location or not
    results = await database_sync_to_async(
        lambda: list(PickupData.objects.filter(
            palletid__location=scanned_location,
            pickupstatus='WAITPICK'
        ).values('pickupid', 'palletid', 'hardwareid'))
    )()

    print(results)

    if len(results) == 0:

        # Employee is at wrong location according to map
        error_type = 'LOCATION'
    
    else:
        pickup_record = results[0]

        if pickup_record['hardwareid'] != hardware_id:

            # Consider other employee's task
            error_type = 'HARDWARE'

        else:
            if pickup_record['palletid'] != scanned_pallet_id:

                # Pallet was moved arbitrarily, and not updated
                error_type = 'PALLET'
            
            else:

                # This job is correct
                verify_pickup_pallet_status = True

                # Update pickup record status
                await database_sync_to_async(
                    lambda: PickupData.objects.filter(pickupid=pickup_record['pickupid']).update(pickupstatus='PICKING')
                )()

                # Update pallet status
                await database_sync_to_async(
                    lambda: PalletData.objects.filter(palletid=scanned_pallet_id).update(palletstatus='PICKING')
                )()

    return verify_pickup_pallet_status, error_type


async def Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id):

    # Initialize status and error type
    verify_pickup_amount_status = False
    error_type = None
    order_info = None


    results = await database_sync_to_async(
        lambda: list(PickupData.objects.filter(palletid=scanned_pallet_id, pickupstatus='PICKING').values(
            'pickupid', 'quantity', 'hardwareid', 'orderlistid', 'orderlistid__ordernumber'
        ))
    )()

    if len(results) == 0:
        
        # Employee didn't do a considered pallet from stage 1
        error_type = 'PALLET'

    else:
        pickup_record = results[0]

        if pickup_record['hardwareid'] != hardware_id:

            # This task is not your job
            error_type = 'HARDWARE'

        else:

            # Verify weight of pallet
            expected_pallet_weight = await database_sync_to_async(
                lambda: PalletData.objects.filter(palletid=scanned_pallet_id).values_list('palletweight', flat=True).last()
            )()

            min_weight, max_weight = commons.Range_expected_weight(expected_pallet_weight)

            if min_weight <= scanned_pallet_weight <= max_weight:
                verify_pickup_amount_status = True

                order_info = {
                    'order_list_id': pickup_record['orderlistid'],
                    'order_number': pickup_record['orderlistid__ordernumber'],
                    'pick_quantity': pickup_record['quantity'],
                    'pickup_id': pickup_record['pickupid']
                }
            else:
                error_type = 'AMOUNT'

    return verify_pickup_amount_status, error_type, order_info

