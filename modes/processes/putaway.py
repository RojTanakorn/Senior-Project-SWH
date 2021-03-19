''' Function for processing putaway mode '''
async def Putaway_mode(its_serial_number, payload_json, current_mode, current_stage):
    
    # Get only hardware ID's sender and employee ID
    hardware_id = its_serial_number[2:]
    employee_id = payload_json['employee_id']

    # Process data in stage 0
    if current_stage == 0:
        await Putaway_stage_0(hardware_id, employee_id, payload_json)

    # Process data in stage 1
    elif current_stage == 1:
        await Putaway_stage_1(hardware_id, employee_id, payload_json)

    # Process data in stage 2
    elif current_stage == 2:
        await Putaway_stage_2(hardware_id, employee_id, payload_json)


''' ****************************************************** '''
''' **************** STAGE FUNCTIONS PART **************** '''
''' ****************************************************** '''

''' Function stage 0 '''
async def Putaway_stage_0(hardware_id, employee_id, payload_json):

    # Initialize error parameters for sending with payload and storing log
    stage_status = False
    error_type = None

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
                location = await Define_location()

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

            # Update data header pf webapp payload
            data.update({'item_name': pallet_info['itemnumber__itemname'], 'location': pallet_info['location']})

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if stage_status else 'ERR',
            'errorfield': error_type,
            'mode_id': 2,
            'stage': 0,
            'scanpallet': scanned_pallet_id,
            'scanpalletweight': scanned_pallet_weight,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s0(status=stage_status, error_type=error_type, data=data)

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


''' Function stage 1 '''
async def Putaway_stage_1(hardware_id, employee_id, payload_json):

    # Get now local datetime
    timestamp = commons.Get_now_local_datetime()

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

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if verify_location_status else 'ERR',
            'errorfield': None if verify_location_status else verify_location_field,
            'mode_id': 2,
            'stage': 1,
            'scanpallet': scanned_pallet_id,
            'scanlocation': scanned_location,
            'employeeid_id': employee_id,
            'logtimestamp': timestamp
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s1(status=verify_location_status, scanned_location=scanned_location)

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


''' Function stage 2 '''
async def Putaway_stage_2(hardware_id, employee_id, payload_json):
    
    # Get data from hardware payload
    scanned_pallet_id = payload_json['pallet_id']
    scanned_location = payload_json['location']
    place_pallet_status = payload_json['status']

    # Store log into LOG_DATA
    await commons.Store_log(
        create_log_dict={
            'logtype': 'GEN' if place_pallet_status else 'ERR',
            'errorfield': 'LOCATION',
            'mode_id': 2,
            'stage': 2,
            'scanpallet': scanned_pallet_id,
            'scanlocation': scanned_location,
            'employeeid_id': employee_id,
            'logtimestamp': commons.Get_now_local_datetime()
        }
    )

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s2(status=place_pallet_status)

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for verifying pallet ID '''
async def Verify_pallet(scanned_pallet_id):

    # Initialize status and item number which are returned
    status = 'UNVERIFY'
    item_number = None

    # Query item number and pallet status of considered pallet ID
    results = await database_sync_to_async(
        lambda: list(PalletData.objects.filter(palletid=scanned_pallet_id).values('itemnumber', 'palletstatus'))
    )()

    # If pallet ID doesn't exist
    if len(results) == 0:
        status = 'NOT EXIST'

    else:

        # Get pallet status and item number
        pallet_status = results[0]['palletstatus']
        item_number = results[0]['itemnumber']

        # If item number is not registered to this pallet ID yet
        if item_number is None:
            status = 'NO ITEM'

        else:

            # If pallet status is 'REGISTER' --> Normal process for putaway
            if pallet_status == 'REGISTER':
                status = 'VERIFY'

            # If pallet status is 'PENDPUT' --> This pallet has already been verified
            elif pallet_status == 'PENDPUT':
                status = 'ALREADY'


    return status, item_number


''' Function for verifying amount of item using weight '''
async def Verify_amount(item_number, scanned_pallet_weight):

    # Get item name, weight per piece, amount per pallet of specific item number
    item_name, weight_per_piece, amount_per_pallet = await database_sync_to_async(
        lambda: ItemData.objects.filter(itemnumber=item_number).values_list('itemname', 'weightperpiece', 'amountperpallet').last()
    )()

    # Calculate range of expected weight
    min_weight, max_weight = Calculate_expected_weight(weight_per_piece, amount_per_pallet)

    # Check that pallet weight is in range of expected weight or not
    verify_amount_status = min_weight <= scanned_pallet_weight <= max_weight
 
    return verify_amount_status, item_name, amount_per_pallet


''' Function for calculate range of expected weight '''
def Calculate_expected_weight(weight_per_piece, amount_per_pallet):

    # Center of expected weight
    expected_weight = commons.EMPTY_PALLET_WEIGHT + (weight_per_piece * amount_per_pallet)

    # Min and max of expected weight
    min_weight, max_weight = commons.Range_expected_weight(expected_weight)

    return min_weight, max_weight


''' Function for defining location '''
async def Define_location():
    # This is mock of defining
    location = await database_sync_to_async(
        lambda: LayoutData.objects.filter(locationstatus='BLANK').values_list('location', flat=True).first()
    )()

    return location


''' Function for booking location '''
async def Book_location(location):
    await database_sync_to_async(
        lambda: LayoutData.objects.filter(location=location).update(locationstatus='BOOK')
    )()


''' Function for verify location from hardware '''
async def Verify_location(scanned_pallet_id, scanned_location):

    # Query palletstatus, location of scanned_pallet_id from PALLET_DATA
    # Get dict of query result (pallet_id is unique, we can get the first one)
    verify_location_query = await database_sync_to_async(
        lambda: list(PalletData.objects.filter(palletid=scanned_pallet_id).values('palletstatus', 'location'))[0]
    )()

    # Is palletstatus is PENDPUT (Pending for putaway)?
    # If it isn't, return false & error field
    # If it is, return result of comparing between scanned_location and location from query
    if verify_location_query['palletstatus'] == 'PENDPUT':
        return ((scanned_location == verify_location_query['location']), 'LOCATION')
    else:
        return (False, 'PALLET STATUS')
