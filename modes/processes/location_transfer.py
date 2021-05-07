from . import commons
from db.models import LocationTransferData, PalletData
from channels.db import database_sync_to_async


''' Function for processing location transfer mode '''
async def Location_transfer_mode(hardware_id, payload_json, current_stage):
    
    # Get employee ID
    employee_id = payload_json['employee_id']

    # Process data in stage 2
    if current_stage == 2:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Location_transfer_stage_2(hardware_id, employee_id, payload_json)

    # Process data in stage 3
    elif current_stage == 3:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Location_transfer_stage_3(hardware_id, employee_id, payload_json)
    
    # Process data in stage 4
    elif current_stage == 4:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Location_transfer_stage_4(hardware_id, employee_id, payload_json)

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
async def Location_transfer_stage_2(hardware_id, employee_id, payload_json):
    
    # Initialize new mode, stage, and location transfer status
    new_mode = None
    new_stage = None
    location_transfer_status = 'WAITMOVE'

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_pallet_weight = payload_json['pallet_weight']
    scanned_location = payload_json['location']

    # Verify pallet and location that is ready to move or not
    verify_source_location_status, error_type, location_transfer_id, location_transfer_info = await Verify_source_location(hardware_id, scanned_pallet_id, scanned_pallet_weight, scanned_location)

    # Get now local datetime
    timestamp = commons.Get_now_local_datetime()

    if verify_source_location_status:
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={'palletstatus': 'MOVING'}
        )

        new_mode = 4
        new_stage = 3
        location_transfer_status = 'MOVING'

    else:
        if error_type in ['PALLET', 'AMOUNT']:
            new_mode = 0
            new_stage = 0
            location_transfer_status = 'REJECT'

            if error_type == 'PALLET':
                
                # Handle pallet rejection which pallet in wanted location is unwanted (wrong)
                await commons.Pallet_rejection_of_pallet_in_wrong_location(
                    unwanted_pallet_id=scanned_pallet_id,
                    wanted_pallet_id=location_transfer_info['wanted_pallet_id'],
                    wanted_location=scanned_location
                )

            elif error_type == 'AMOUNT':
                
                # Handle pallet rejection which pallet has wrong amount of item
                await commons.Pallet_rejection_of_pallet_amount(scanned_pallet_id)

            # Restore destination location status from BOOK to BLANK (unbook)
            await commons.Update_location_info(
                location=location_transfer_info['destination_location'],
                update_info_dict={'locationstatus': 'BLANK'}
            )
    
    if error_type != 'STATUS':
        await database_sync_to_async(
            lambda: LocationTransferData.objects.filter(locationtransferid=location_transfer_id).update(
                locationtransferstatus=location_transfer_status, statustimestamp=None if location_transfer_status=='WAITMOVE' else timestamp
            )
        )()

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if verify_source_location_status else 'ERR',
        'errorfield': error_type,
        'mode_id': 4,
        'stage': 2,
        'scanpallet': scanned_pallet_id,
        'scanpalletweight': scanned_pallet_weight,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': timestamp
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m4s2(
        status=verify_source_location_status,
        new_mode=new_mode,
        new_stage=new_stage,
        error_type=error_type,
        scanned_location=scanned_location
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage
    

''' Function stage 3 '''
async def Location_transfer_stage_3(hardware_id, employee_id, payload_json):
    
    # Initialize new mode, stage, and location transfer status
    new_mode = None
    new_stage = None

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    verify_destination_location_status, error_type = await Verify_destination_location(hardware_id, scanned_pallet_id, scanned_location)

    # Pallet can be placed at new location
    if verify_destination_location_status:
        new_mode = 4
        new_stage = 4

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if verify_destination_location_status else 'ERR',
        'errorfield': error_type,
        'mode_id': 4,
        'stage': 3,
        'scanpallet': scanned_pallet_id,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': commons.Get_now_local_datetime()
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m4s3(
        status=verify_destination_location_status,
        new_mode=new_mode,
        new_stage=new_stage,
        error_type=error_type,
        scanned_location=scanned_location
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' Function stage 4 '''
async def Location_transfer_stage_4(hardware_id, employee_id, payload_json):

    # Initialize new mode and stage
    new_mode = None
    new_stage = None

    # Initialize location transfer infomation
    total_location_transfer = None
    done_location_transfer = None
    data = None

    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']
    place_pallet_status = payload_json['status']

    # Get now local datetime
    timestamp = commons.Get_now_local_datetime()

    if place_pallet_status:
        
        # Update new location and status of considered pallet
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={'location': scanned_location, 'palletstatus': 'GENERAL'}
        )

        # Get location transfer ID and source location to update data
        location_transfer_id, source_location = await database_sync_to_async(
            lambda: LocationTransferData.objects.filter(locationtransferstatus='MOVING', hardwareid=hardware_id).values_list(
                'locationtransferid', 'sourcelocation'
            ).last()
        )()

        # Update status of source location to be 'BLANK'
        await commons.Update_location_info(
            location=source_location,
            update_info_dict={'locationstatus': 'BLANK'}
        )

        # Update status of new location to be 'BUSY'
        await commons.Update_location_info(
            location=scanned_location,
            update_info_dict={'locationstatus': 'BUSY'}
        )

        # Update location transfer status to be 'SUCCESS'
        await database_sync_to_async(
            lambda: LocationTransferData.objects.filter(locationtransferid=location_transfer_id).update(
                locationtransferstatus='SUCCESS', statustimestamp=timestamp
            )
        )()

        # Get other location transfer orders of hardwaare for notifying
        remain_location_transfer_orders = await commons.Get_remain_location_transfer_list(hardware_id)

        total_location_transfer = remain_location_transfer_orders['total_location_transfer']
        done_location_transfer = remain_location_transfer_orders['done_location_transfer']
        data = remain_location_transfer_orders['data']

        # If location transfer task is done for now
        if len(data) == 0:
            new_mode = 0
            new_stage = 0
        else:
            new_mode = 4
            new_stage = 2

    # Generate dict of log
    log_dict = {
        'logtype': 'GEN' if place_pallet_status else 'ERR',
        'errorfield': None if place_pallet_status else 'LOCATION',
        'mode_id': 4,
        'stage': 4,
        'scanpallet': scanned_pallet_id,
        'scanlocation': scanned_location,
        'employeeid_id': employee_id,
        'logtimestamp': timestamp
    }

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m4s4(
        status=place_pallet_status,
        new_mode=new_mode,
        new_stage=new_stage,
        scanned_location=scanned_location,
        total_location_transfer=total_location_transfer,
        done_location_transfer=done_location_transfer,
        data=data
    )

    return log_dict, hardware_payload, webapp_payload, new_mode, new_stage


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for verifying current location '''
async def Verify_source_location(hardware_id, scanned_pallet_id, scanned_pallet_weight, scanned_location):
    
    # Initialize verify status and error type
    verify_source_location = False
    error_type = None
    location_transfer_id = None
    location_transfer_info = None
    # wanted_pallet_id = None

    location_transfer_result = await database_sync_to_async(
        lambda: LocationTransferData.objects.filter(sourcelocation=scanned_location).values(
            'locationtransferid', 'palletid', 'palletid__palletweight', 'destinationlocation', 'locationtransferstatus', 'hardwareid'
        ).order_by('locationtransferid').last()
    )()

    if location_transfer_result is None:

        # No task for this source location
        error_type = 'LOCATION'

    else:
        
        location_transfer_id = location_transfer_result['locationtransferid']
        # wanted_pallet_id = location_transfer_result['palletid']

        location_transfer_info = {
            'wanted_pallet_id': location_transfer_result['palletid'],
            'destination_location': location_transfer_result['destinationlocation']
        }

        if location_transfer_result['hardwareid'] != hardware_id:
            error_type = 'HARDWARE'

        elif location_transfer_result['locationtransferstatus'] != 'WAITMOVE':
            error_type = 'STATUS'
        
        elif location_transfer_result['palletid'] != scanned_pallet_id:
            error_type = 'PALLET'

        else:
            # Get main-max of expected weight
            min_weight, max_weight = commons.Range_expected_weight(location_transfer_result['palletid__palletweight'])

            if min_weight <= scanned_pallet_weight <= max_weight:
                verify_source_location = True

            else:
                error_type = 'AMOUNT'

    return verify_source_location, error_type, location_transfer_id, location_transfer_info


''' Function for verifying new location '''
async def Verify_destination_location(hardware_id, scanned_pallet_id, scanned_location):
    
    # Initialize verify status and error type
    verify_destination_location = False
    error_type = None

    location_transfer_result = await database_sync_to_async(
        lambda: LocationTransferData.objects.filter(locationtransferstatus='MOVING', hardwareid=hardware_id).values(
            'palletid', 'destinationlocation'
        ).last()
    )()

    if location_transfer_result['palletid'] != scanned_pallet_id:

        # pallet ID is different from stage 2
        error_type = 'PALLET'

    elif location_transfer_result['destinationlocation'] != scanned_location:

        # Employee goes to wrong location
        error_type = 'LOCATION'

    else:

        # Location is ready to place
        verify_destination_location = True

    return verify_destination_location, error_type