from channels.db import database_sync_to_async
from . import commons
from django.db.models import F, Sum
from db.models import OrderData, OrderListData


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

    # Verify scanned pallet and location
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

    # Verify amount in pallet
    verify_pickup_amount_status, error_type, order_info = await Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id)

    # Initialize variables for sending to webapp
    total_pickup = None
    done_pickup = None
    data = None

    # If amount is correct
    if verify_pickup_amount_status:
        
        # Update all information about picking up in related tables
        await Update_data_after_pickup(scanned_pallet_id, order_info)

        # Get data about remaining pickup list
        remain_pickup_info = await commons.Get_remain_pickup_list(hardware_id)

        total_pickup = remain_pickup_info['total_pickup']
        done_pickup = remain_pickup_info['done_pickup']
        data = remain_pickup_info['data']

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

''' Function for verifying pickup pallet '''
async def Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id):

    # Initialize status and error type
    verify_pickup_pallet_status = False
    error_type = None

    # Check that employee go to correct pallet & location or not
    pickup_info_results = await commons.Get_pickup_info_various_filters(
        filters_dict={'palletid__location':scanned_location, 'pickupstatus':'WAITPICK'},
        wanted_fields=('pickupid', 'palletid', 'hardwareid')
    )

    if len(pickup_info_results) == 0:

        # Employee is at wrong location according to map
        error_type = 'LOCATION'
    
    else:
        pickup_info = pickup_info_results[0]

        if pickup_info['hardwareid'] != hardware_id:

            # Consider other employee's task
            error_type = 'HARDWARE'

        else:
            if pickup_info['palletid'] != scanned_pallet_id:

                # Pallet was moved arbitrarily, and not updated
                error_type = 'PALLET'
            
            else:

                # This job is correct
                verify_pickup_pallet_status = True

                # Update pickup record status
                await commons.Update_pickup_info(
                    pickup_id=pickup_info['pickupid'],
                    update_info_dict={'pickupstatus': 'PICKING'}
                )

                # Update pallet status
                await commons.Update_pallet_info(
                    pallet_id=scanned_pallet_id,
                    update_info_dict={'palletstatus': 'PICKING'}
                )

    return verify_pickup_pallet_status, error_type


''' Function for verifying pickup amount '''
async def Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id):

    # Initialize status and error type
    verify_pickup_amount_status = False
    error_type = None
    order_info = None

    # Get information about scanned pallet ID which is being picked up
    pickup_info_results = await commons.Get_pickup_info_various_filters(
        filters_dict={'palletid':scanned_pallet_id, 'pickupstatus':'PICKING'},
        wanted_fields=('pickupid', 'quantity', 'hardwareid', 'orderlistid', 'orderlistid__ordernumber')
    )

    if len(pickup_info_results) == 0:
        
        # Employee didn't do a considered pallet from stage 1
        error_type = 'PALLET'

    else:
        pickup_info = pickup_info_results[0]

        if pickup_info['hardwareid'] != hardware_id:

            # This task is not your job
            error_type = 'HARDWARE'

        else:

            # Verify weight of pallet
            expected_pallet_weight = (await commons.Get_pallet_info(
                pallet_id=scanned_pallet_id,
                wanted_fields=('palletweight',)
            ))['palletweight']

            # Get main-max of expected weight
            min_weight, max_weight = commons.Range_expected_weight(expected_pallet_weight)

            # If scanned pallet weight is in expected range
            if min_weight <= scanned_pallet_weight <= max_weight:
                verify_pickup_amount_status = True

                # Generate data to use outside function
                order_info = {
                    'order_list_id': pickup_info['orderlistid'],
                    'order_number': pickup_info['orderlistid__ordernumber'],
                    'pick_quantity': pickup_info['quantity'],
                    'pickup_id': pickup_info['pickupid']
                }
            else:
                error_type = 'AMOUNT'

    return verify_pickup_amount_status, error_type, order_info


''' Function for updating all information after finish picking up stage 2 '''
async def Update_data_after_pickup(scanned_pallet_id, order_info):
    
    # Update pallet status as PICKED
    await commons.Update_pallet_info(
        pallet_id=scanned_pallet_id,
        update_info_dict={'palletstatus': 'PICKED'}
    )

    # Update location status as 'BLANK'
    location = (await commons.Get_pallet_info(
        pallet_id=scanned_pallet_id,
        wanted_fields=('location',)
    ))['location']

    await commons.Update_location_info(
        location=location,
        update_info_dict={'locationstatus': 'BLANK'}
    )

    # Update pickup status as PICKED
    await commons.Update_pickup_info(
        pickup_id=order_info['pickup_id'],
        update_info_dict={'pickupstatus': 'PICKED'}
    )

    # Update remain pickup quantity of that list
    await Update_remain_pickup_quantity(
        order_list_id=order_info['order_list_id'],
        pick_quantity=order_info['pick_quantity']
    )

    # Check and update order status to:
    #   - PICKING (if order number isn't picked up completely)
    #   - PICKED (if order number is picked up completely)
    await Check_and_update_order_status(order_info['order_number'])


''' Function for updating remain pickup quantity in ORDER_LIST_DATA '''
async def Update_remain_pickup_quantity(order_list_id, pick_quantity):
    await database_sync_to_async(
        lambda: OrderListData.objects.filter(orderlistid=order_list_id).update(
            remainpickupquantity=F('remainpickupquantity') - pick_quantity
        )
    )()


''' Function for Checking and updating order status '''
async def Check_and_update_order_status(order_number):
    remain_pickup_quantity_sum = await database_sync_to_async(
        lambda: OrderListData.objects.filter(
            ordernumber=order_number
        ).aggregate(Sum('remainpickupquantity'))['remainpickupquantity__sum']
    )()

    if bool(remain_pickup_quantity_sum):
        order_status = 'PICKING'
    else:
        order_status = 'PICKED'
            
    await database_sync_to_async(
        lambda: OrderData.objects.filter(ordernumber=order_number).update(orderstatus=order_status)
    )()