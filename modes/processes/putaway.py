from channels.db import database_sync_to_async
from . import commons
from db.models import LayoutData, ItemData


''' **************************************************** '''
''' **************** MAIN FUNCTION PART **************** '''
''' **************************************************** '''

''' Function for processing putaway mode '''

async def Putaway_mode(hardware_id, payload_json, current_stage):
    employee_id = payload_json['employee_id']

    # Process data in stage 1
    if current_stage == 1:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Putaway_stage_1(
            employee_id, payload_json
        )

    # Process data in stage 2
    elif current_stage == 2:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Putaway_stage_2(
            employee_id, payload_json
        )

    # Process data in stage 3
    elif current_stage == 3:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Putaway_stage_3(
            employee_id, payload_json
        )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage

    # # Store log into LOG_DATA
    # await commons.Store_log(
    #     create_log_dict=log_dict
    # )

    # # Send payload to clients
    # await commons.Notify_clients(
    #     hardware_id=hardware_id,
    #     hardware_payload=hardware_payload,
    #     webapp_payload=webapp_payload
    # )

    # if new_mode is not None:
    #     await commons.Update_current_mode_stage(
    #         hardware_id=hardware_id,
    #         mode=new_mode,
    #         stage=new_stage
    #     )


''' ****************************************************** '''
''' **************** STAGE FUNCTIONS PART **************** '''
''' ****************************************************** '''

''' Function stage 1 '''
async def Putaway_stage_1(employee_id, payload_json):

    # Initialize error parameters for sending with payload and storing log
    stage_status = False
    error_type = None
    new_mode = 0
    new_stage = 0

    # Initialize dict of data about item and location
    data = {
        'item_number': None,
        'item_name': None,
        'location': None
    }

    # Extract data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_pallet_weight = payload_json['pallet_weight']

    # Verify pallet ID and getting status for checking
    verify_pallet_status, item_number = await Verify_pallet(scanned_pallet_id)

    # Update data header pf webapp payload
    data.update({'item_number': item_number})

    # Status is not in 'ALREADY', 'VERIFY' ---> cannot be used
    if verify_pallet_status not in ['ALREADY', 'VERIFY']:
        error_type = verify_pallet_status

    # Status is in 'ALREADY', 'VERIFY' ---> desired
    else:

        # Pallet ID is verify
        if verify_pallet_status == 'VERIFY':

            # Verify amount of item in pallet using scanned pallet weight
            verify_amount_status, item_name, amount_per_pallet = await Verify_amount(item_number, scanned_pallet_weight)

            # Update data header pf webapp payload
            data.update({'item_name': item_name})

            # If amount of item is correct
            if verify_amount_status:

                # Define location that be used to store pallet
                location = await Define_location(item_number)

                # Update data header pf webapp payload
                data.update({'location': location})

                # If there is available location
                if location is not None:

                    # Book location we want to store pallet
                    await Book_location(location)

                    # Update pallet information and set status from 'REGISTER' to 'PENDPUT'
                    await commons.Update_pallet_info(
                        pallet_id=scanned_pallet_id,
                        update_info_dict={
                            'amountofitem': amount_per_pallet,
                            'amountavailable': amount_per_pallet,
                            'palletweight': scanned_pallet_weight,
                            'palletstatus': 'PENDPUT',
                            'location': location
                        }
                    )

                    # status about working correctly
                    stage_status = True

                    # define new mode and stage
                    new_mode = 2
                    new_stage = 2

                # There is no available location
                else:
                    error_type = 'NO LOCATION'
            
            # If amount of item is incorrect
            else:
                error_type = 'AMOUNT'

        # Pallet ID has already been verified
        else:
            error_type = verify_pallet_status
            
            # Get pallet information for displaying where the pallet should be stored, and also display item name
            pallet_info = await commons.Get_pallet_info(
                pallet_id=scanned_pallet_id,
                wanted_fields=('itemnumber__itemname', 'location')
            )

            # define new mode and stage
            new_mode = 2
            new_stage = 2

            # Update data header pf webapp payload
            data.update({'item_name': pallet_info['itemnumber__itemname'], 'location': pallet_info['location']})

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if stage_status else 'ERR',
        'errorfield': error_type,
        'mode_id': 2,
        'stage': 1,
        'scanpallet': scanned_pallet_id,
        'scanpalletweight': scanned_pallet_weight,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s1(
        status=stage_status,
        new_mode=new_mode,
        new_stage=new_stage,
        error_type=error_type,
        data=data
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' Function stage 2 '''
async def Putaway_stage_2(employee_id, payload_json):

    # Initialize new mode and stage
    new_mode = None
    new_stage = None

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    # Verify location from hardware
    verify_location_status, verify_location_field = await Verify_location(
        scanned_pallet_id,
        scanned_location
    )

    # When verify location is passed
    if verify_location_status:

        new_mode = 2
        new_stage = 3

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if verify_location_status else 'ERR',
        'errorfield': None if verify_location_status else verify_location_field,
        'mode_id': 2,
        'stage': 2,
        'scanpallet': scanned_pallet_id,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s2(
        status=verify_location_status,
        new_mode=new_mode,
        new_stage=new_stage,
        scanned_location=scanned_location
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' Function stage 3 '''
async def Putaway_stage_3(employee_id, payload_json):
    
    # Get now local datetime
    timestamp = commons.Get_now_local_datetime()

    # Initialize new mode and stage
    new_mode = None
    new_stage = None

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']
    place_pallet_status = payload_json['status']

    if place_pallet_status:
        new_mode = 2
        new_stage = 1

        # Update palletstatus & putawaytimestamp on PALLET_DATA
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={
                'palletstatus': 'GENERAL',
                'putawaytimestamp': timestamp
            }
        )

        # Update locationstatus on LAYOUT_DATA
        await commons.Update_location_info(
            location=scanned_location,
            update_info_dict={
                'locationstatus': 'BUSY'
            }
        )

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if place_pallet_status else 'ERR',
        'errorfield': None if place_pallet_status else 'LOCATION',
        'mode_id': 2,
        'stage': 3,
        'scanpallet': scanned_pallet_id,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s3(
        status=place_pallet_status,
        new_mode=new_mode,
        new_stage=new_stage,
        scanned_location=scanned_location
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for verifying pallet ID '''
async def Verify_pallet(scanned_pallet_id):

    # Initialize status and item number which are returned
    status = 'UNVERIFY'
    item_number = None

    # Query item number and pallet status of considered pallet ID
    pallet_info = await commons.Get_pallet_info(
        pallet_id=scanned_pallet_id,
        wanted_fields=('itemnumber', 'palletstatus')
    )

    # If pallet ID doesn't exist
    if pallet_info is None:
        status = 'NOT EXIST'

    else:

        # If item number is not registered to this pallet ID yet
        if pallet_info['itemnumber'] is None:
            status = 'NO ITEM'

        else:

            item_number = pallet_info['itemnumber']

            # If pallet status is 'REGISTER' --> Normal process for putaway
            if pallet_info['palletstatus'] == 'REGISTER':
                status = 'VERIFY'

            # If pallet status is 'PENDPUT' --> This pallet has already been verified
            elif pallet_info['palletstatus'] == 'PENDPUT':
                status = 'ALREADY'

    return status, item_number


''' Function for verifying amount of item using weight '''
async def Verify_amount(item_number, scanned_pallet_weight):

    # Get item name, weight per piece, amount per pallet of specific item number
    item_info = await commons.Get_item_info(
        item_number=item_number,
        wanted_fields=('itemname', 'weightperpiece', 'amountperpallet')
    )

    # Calculate range of expected weight
    min_weight, max_weight = Calculate_expected_weight(item_info['weightperpiece'], item_info['amountperpallet'])

    # Check that pallet weight is in range of expected weight or not
    verify_amount_status = min_weight <= scanned_pallet_weight <= max_weight
 
    return verify_amount_status, item_info['itemname'], item_info['amountperpallet']


''' Function for calculate range of expected weight '''
def Calculate_expected_weight(weight_per_piece, amount_per_pallet):

    # Center of expected weight
    expected_weight = commons.EMPTY_PALLET_WEIGHT + (weight_per_piece * amount_per_pallet)

    # Min and max of expected weight
    min_weight, max_weight = commons.Range_expected_weight(expected_weight, weight_per_piece)

    return min_weight, max_weight


''' Function for defining location '''
async def Define_location(item_number):
    
    row = await database_sync_to_async(
        lambda: ItemData.objects.filter(itemnumber=item_number).values_list('itemgroup__row', flat=True).first()
    )()

    location = await database_sync_to_async(
        lambda: LayoutData.objects.filter(locationstatus='BLANK', row=row).values_list('location', flat=True).first()
    )()

    return location


''' Function for booking location '''
async def Book_location(location):
    await commons.Update_location_info(
        location=location,
        update_info_dict={'locationstatus': 'BOOK'}
    )


''' Function for verify location from hardware '''
async def Verify_location(scanned_pallet_id, scanned_location):

    # Query palletstatus, location of scanned_pallet_id from PALLET_DATA
    # Get dict of query result (pallet_id is unique, we can get the first one)
    verify_location_query = await commons.Get_pallet_info(
        pallet_id=scanned_pallet_id,
        wanted_fields=('palletstatus', 'location')
    )

    # Is palletstatus is PENDPUT (Pending for putaway)?
    # If it isn't, return false & error field
    # If it is, return result of comparing between scanned_location and location from query
    if verify_location_query['palletstatus'] == 'PENDPUT':
        return ((scanned_location == verify_location_query['location']), 'LOCATION')
    else:
        return (False, 'PALLET STATUS')
