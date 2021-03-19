from . import commons


''' Function for processing location transfer mode '''
async def Location_transfer_mode(its_serial_number, payload_json, current_mode, current_stage):
    
    # Get only hardware ID's sender and employee ID
    hardware_id = its_serial_number[2:]
    employee_id = payload_json['employee_id']

    # Process data in stage 0
    if current_stage == 0:
        await Location_transfer_stage_0(hardware_id, employee_id, payload_json)

    # Process data in stage 1
    elif current_stage == 1:
        await Location_transfer_stage_1(hardware_id, employee_id, payload_json)


''' ****************************************************** '''
''' **************** STAGE FUNCTIONS PART **************** '''
''' ****************************************************** '''

''' Function stage 0 '''
async def Location_transfer_stage_0(hardware_id, employee_id, payload_json):
    
    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    # Verify pallet and location that is ready to move or not
    verify_current_location, error_type = await Verify_current_location(scanned_pallet_id, scanned_location)

    if verify_current_location:
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={'palletstatus': 'MOVING'}
        )

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if verify_current_location else 'ERR',
            'errorfield': error_type,
            'mode_id': 4,
            'stage': 0,
            'scanpallet': scanned_pallet_id,
            'scanlocation': scanned_location,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m4s0(status=verify_current_location, error_type=error_type)

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )

''' Function stage 1 '''
async def Location_transfer_stage_1(hardware_id, employee_id, payload_json):
    
    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']

    verify_new_location, error_type, current_location = await Verify_new_location(scanned_pallet_id, scanned_location)

    # Pallet can be placed at new location
    if verify_new_location:

        # Update new location and status of considered pallet
        await commons.Update_pallet_info(
            pallet_id=scanned_pallet_id,
            update_info_dict={'location': scanned_location, 'palletstatus': 'GENERAL'}
        )

        # Update status of current location as 'BLANK'
        await commons.Update_location_info(
            location=current_location,
            update_info_dict={'locationstatus': 'BLANK'}
        )

        # Update status of new location as 'BUSY'
        await commons.Update_location_info(
            location=scanned_location,
            update_info_dict={'locationstatus': 'BUSY'}
        )

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if verify_new_location else 'ERR',
            'errorfield': error_type,
            'mode_id': 4,
            'stage': 1,
            'scanpallet': scanned_pallet_id,
            'scanlocation': scanned_location,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m4s1(status=verify_new_location, error_type=error_type)

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for verifying current location '''
async def Verify_current_location(scanned_pallet_id, scanned_location):
    
    # Initialize verify status and error type
    verify_current_location = False
    error_type = None

    # Get information of scanned pallet
    scanned_pallet_info = await commons.Get_pallet_info(
        pallet_id=scanned_pallet_id,
        wanted_fields=('palletstatus', 'location')
    )

    if scanned_pallet_info['palletstatus'] != 'GENERAL':

        # Pallet isn't ready to move
        error_type = 'STATUS'

    else:
        if scanned_pallet_info['location'] != scanned_location:

            # Pallet was moved arbitrarily
            error_type = 'LOCATION'

        else:

            # Pallet is ready to move
            verify_current_location = True

    return verify_current_location, error_type


''' Function for verifying new location '''
async def Verify_new_location(scanned_pallet_id, scanned_location):
    
    # Initialize verify status and error type
    verify_new_location = False
    error_type = None

    # Get information of scanned pallet
    scanned_pallet_info = await commons.Get_pallet_info(
        pallet_id=scanned_pallet_id,
        wanted_fields=('palletstatus', 'location')
    )

    # Get information of scanned location
    scanned_location_info = await commons.Get_location_info(
        location=scanned_location,
        wanted_fields=('locationstatus',)
    )

    if scanned_pallet_info['palletstatus'] != 'MOVING':

        # Pallet doesn't pass stage 0
        error_type = 'PALLET'

    else:
        if scanned_location_info['locationstatus'] != 'BLANK':

            # Location isn't ready to place pallet (BOOK or BUSY)
            error_type = 'LOCATION'

        else:

            # Location is ready to place
            verify_new_location = True

    return verify_new_location, error_type, scanned_pallet_info['location']