from channels.db import database_sync_to_async
from . import commons
from django.db.models import F, Sum
from db.models import OrderData, OrderListData, PalletData


''' **************************************************** '''
''' **************** MAIN FUNCTION PART **************** '''
''' **************************************************** '''

''' Function for processing pickup mode '''
async def Pickup_mode(its_serial_number, payload_json, current_stage):
    
    # Get only hardware ID's sender and employee ID
    hardware_id = its_serial_number[2:]
    employee_id = payload_json['employee_id']

    # Process data in stage 2
    if current_stage == 2:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Pickup_stage_2(hardware_id, employee_id, payload_json)

    # Process data in stage 3
    elif current_stage == 3:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Pickup_stage_3(hardware_id, employee_id, payload_json)

    # Process data in stage 4
    elif current_stage == 4:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Pickup_stage_4(hardware_id, employee_id)

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict=log_dict
    )

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )

    # Update current mode and stage in database
    if new_mode is not None:
        await commons.Update_current_mode_stage(hardware_id=hardware_id, mode=new_mode, stage=new_stage)

    
''' ****************************************************** '''
''' **************** STAGE FUNCTIONS PART **************** '''
''' ****************************************************** '''

''' Function stage 2 '''
async def Pickup_stage_2(hardware_id, employee_id, payload_json):
    
    # Initialize new mode and stage
    new_mode = 3
    new_stage = 3

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    # Verify scanned pallet and location
    verify_pickup_pallet_status, error_type, pickup_info = await Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id)

    # If pallet ID and location are correct
    if verify_pickup_pallet_status:
        
        # Update pickup record status
        await commons.Update_pickup_info(
            pickup_id=pickup_info['pickup_id'],
            update_info_dict={'pickupstatus': 'PICKING'}
        )

        # Update pallet status
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={'palletstatus': 'PICKING'}
        )

    else:

        # Location is wrong or task is not assigned for this hardware
        if error_type in ['LOCATION', 'HARDWARE']:
            new_mode = None
            new_stage = None
        
        # Pallet is in wrong location
        elif error_type == 'PALLET':
            
            # Reject -> go to selection mode page
            new_mode = 0
            new_stage = 0

            # Handle pallet rejection which pallet in wanted location is unwanted (wrong)
            await commons.Pallet_rejection_of_pallet_in_wrong_location(
                unwanted_pallet_id=scanned_pallet_id,
                wanted_pallet_id=pickup_info['wanted_pallet_id'],
                wanted_location=scanned_location
            )

            # Define new pallet ID to considered pickup ID
            await Define_new_pallet_to_pickup(pickup_id=pickup_info['pickup_id'])

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if verify_pickup_pallet_status else 'ERR',
        'errorfield': error_type,
        'mode_id': 3,
        'stage': 2,
        'scanpallet': scanned_pallet_id,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m3s2(
        status=verify_pickup_pallet_status,
        new_mode=new_mode,
        new_stage=new_stage,
        error_type=error_type,
        scanned_location=scanned_location
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' Function stage 3 '''
async def Pickup_stage_3(hardware_id, employee_id, payload_json):
    
    # Initialize new mode and stage
    new_mode = 3
    new_stage = 4

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_pallet_weight = payload_json['pallet_weight']

    # Verify amount in pallet
    verify_pickup_amount_status, error_type, pickup_info = await Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id)

    # If amount is correct
    if verify_pickup_amount_status:

        # Update all information about picking up in related tables
        await Update_data_after_pickup(scanned_pallet_id, pickup_info)
    
    else:

        # pallet is wrong or task is not assigned for this hardware
        if error_type in ['PALLET', 'HARDWARE']:
            new_mode = None
            new_stage = None
        
        # Amount is not correct
        elif error_type == 'AMOUNT':

            # Reject -> go to selection mode page
            new_mode = 0
            new_stage = 0

            # Handle pallet rejection which pallet has wrong amount of item
            await commons.Pallet_rejection_of_pallet_amount(scanned_pallet_id)

            # Define new pallet ID to considered pickup ID
            await Define_new_pallet_to_pickup(pickup_id=pickup_info['pickup_id'])

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if verify_pickup_amount_status else 'ERR',
        'errorfield': error_type,
        'mode_id': 3,
        'stage': 3,
        'scanpallet': scanned_pallet_id,
        'scanpalletweight': scanned_pallet_weight,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m3s3(
        status=verify_pickup_amount_status,
        new_mode=new_mode,
        new_stage=new_stage,
        error_type=error_type
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' Function stage 4 '''
async def Pickup_stage_4(hardware_id, employee_id):
    
    # Initialize new mode and stage
    new_mode = 3
    new_stage = 2

    # Initialize variables for sending to webapp
    total_pickup = None
    done_pickup = None
    data = None

    # Get data about remaining pickup list
    remain_pickup_info = await commons.Get_remain_pickup_list(hardware_id)

    total_pickup = remain_pickup_info['total_pickup']
    done_pickup = remain_pickup_info['done_pickup']
    data = remain_pickup_info['data']

    # If pickup task is done for today
    if len(data) == 0:
        new_mode = 0
        new_stage = 0

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN',
        'mode_id': 3,
        'stage': 4,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m3s4(
        new_mode=new_mode,
        new_stage=new_stage,
        total_pickup=total_pickup,
        done_pickup=done_pickup,
        data=data
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for verifying pickup pallet '''
async def Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id):

    # Initialize status, error type, and pickup information
    verify_pickup_pallet_status = False
    error_type = None
    pickup_info_dict = None

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

        pickup_info_dict = {
            'pickup_id': pickup_info['pickupid'],
            'wanted_pallet_id': pickup_info['palletid']
        }

    return verify_pickup_pallet_status, error_type, pickup_info_dict


''' Function for verifying pickup amount '''
async def Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id):

    # Initialize status and error type
    verify_pickup_amount_status = False
    error_type = None
    pickup_info_dict = None

    # Get information about scanned pallet ID which is being picked up
    pickup_info_results = await commons.Get_pickup_info_various_filters(
        filters_dict={'palletid':scanned_pallet_id, 'pickupstatus':'PICKING'},
        wanted_fields=('pickupid', 'quantity', 'hardwareid', 'orderlistid', 'orderlistid__ordernumber', 'palletid__itemnumber')
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

            # Generate data to use outside function
            pickup_info_dict = {
                'order_list_id': pickup_info['orderlistid'],
                'order_number': pickup_info['orderlistid__ordernumber'],
                'pick_quantity': pickup_info['quantity'],
                'pickup_id': pickup_info['pickupid'],
                'item_number': pickup_info['palletid__itemnumber']
            }

            # Get main-max of expected weight
            min_weight, max_weight = commons.Range_expected_weight(expected_pallet_weight)

            # If scanned pallet weight is in expected range
            if min_weight <= scanned_pallet_weight <= max_weight:
                verify_pickup_amount_status = True

            else:
                error_type = 'AMOUNT'

    return verify_pickup_amount_status, error_type, pickup_info_dict


''' Function for updating all information after finish picking up stage 3 '''
async def Update_data_after_pickup(scanned_pallet_id, pickup_info):
    
    # Update pallet status as PICKED
    await commons.Update_pallet_info(
        pallet_id=scanned_pallet_id,
        update_info_dict={'palletstatus': 'PICKED', 'location': None}
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
        pickup_id=pickup_info['pickup_id'],
        update_info_dict={'pickupstatus': 'PICKED'}
    )

    # Update remain pickup quantity of that list
    await Update_remain_pickup_quantity(
        order_list_id=pickup_info['order_list_id'],
        pick_quantity=pickup_info['pick_quantity']
    )

    # Check and update order status to:
    #   - PICKING (if order number isn't picked up completely)
    #   - PICKED (if order number is picked up completely)
    await Check_and_update_order_status(pickup_info['order_number'])


''' Function for updating remain pickup quantity in ORDER_LIST_DATA '''
async def Update_remain_pickup_quantity(order_list_id, pick_quantity):
    await database_sync_to_async(
        lambda: OrderListData.objects.filter(orderlistid=order_list_id).update(
            remainpickupquantity=F('remainpickupquantity') - pick_quantity
        )
    )()


''' Function for Checking and updating order status '''
async def Check_and_update_order_status(order_number):

    # Get sum of remained pickup quantity in specific order number
    remain_pickup_quantity_sum = await database_sync_to_async(
        lambda: OrderListData.objects.filter(
            ordernumber=order_number
        ).aggregate(Sum('remainpickupquantity'))['remainpickupquantity__sum']
    )()

    # If sum != 0
    if bool(remain_pickup_quantity_sum):
        order_status = 'PICKING'
    
    # If sum = 0
    else:
        order_status = 'PICKED'
    
    # Update order status
    await database_sync_to_async(
        lambda: OrderData.objects.filter(ordernumber=order_number).update(orderstatus=order_status)
    )()


''' Function for defining new pallet ID for pickup task when old pallet ID is rejected '''
async def Define_new_pallet_to_pickup(pickup_id):
    
    # Get wanted item number
    wanted_item_number = (
        await commons.Get_pickup_info_various_filters(
            filters_dict={'pickupid': pickup_id},
            wanted_fields=('palletid__itemnumber',)
        )
    )[0]['palletid__itemnumber']

    # Find new pallet ID that is the same item number ordered by putaway timestamp
    new_pallet_id = await database_sync_to_async(
        lambda: PalletData.objects.filter(itemnumber=wanted_item_number, palletstatus='GENERAL').values_list('palletid', flat=True).order_by('putawaytimestamp').first()
    )()

    # Update data of new pallet ID
    await commons.Update_pallet_info(
        pallet_id=new_pallet_id,
        update_info_dict={'palletstatus': 'WAITPICK', 'amountavailable': 0}
    )

    # Define new pallet ID in pickup ID
    await commons.Update_pickup_info(
        pickup_id=pickup_id,
        update_info_dict={'palletid': new_pallet_id, 'pickupstatus': 'WAITPICK'}
    )