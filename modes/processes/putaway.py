from channels.db import database_sync_to_async
from . import commons
from .commons import Update_pallet_info, Get_pallet_info, Get_now_local_datetime, Store_log, Notify_clients, EMPTY_PALLET_WEIGHT, PALLET_WEIGHT_ERROR
from db.models import PalletData, ItemData, LayoutData
from asgiref.sync import sync_to_async


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
                    await Update_pallet_info(
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
            pallet_info = await Get_pallet_info(
                pallet_id=scanned_pallet_id,
                wanted_fields=('itemnumber__itemname', 'location')
            )

            # Update data header pf webapp payload
            data.update({'item_name': pallet_info['itemnumber__itemname'], 'location': pallet_info['location']})

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.m2s0(status=stage_status, error_type=error_type, data=data)

    # Store log into LOG_DATA
    await Store_log(
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

    # Send payload to clients
    await Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )


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


async def Verify_amount(item_number, scanned_pallet_weight):
    item_name, weight_per_piece, amount_per_pallet = await database_sync_to_async(
        lambda: ItemData.objects.filter(itemnumber=item_number).values_list('itemname', 'weightperpiece', 'amountperpallet').last()
    )()

    min_weight, max_weight = Calculate_expected_weight(weight_per_piece, amount_per_pallet)

    verify_amount_status = min_weight <= scanned_pallet_weight <= max_weight
 
    return verify_amount_status, item_name, amount_per_pallet


def Calculate_expected_weight(weight_per_piece, amount_per_pallet):
    expected_weight = EMPTY_PALLET_WEIGHT + (weight_per_piece * amount_per_pallet)

    min_weight = (1 - PALLET_WEIGHT_ERROR) * expected_weight
    max_weight = (1 + PALLET_WEIGHT_ERROR) * expected_weight

    return min_weight, max_weight


async def Define_location():
    # This is mock of defining
    location = await database_sync_to_async(
        lambda: LayoutData.objects.filter(locationstatus='BLANK').values_list('location', flat=True).first()
    )()

    return location


async def Book_location(location):
    await database_sync_to_async(
        lambda: LayoutData.objects.filter(location=location).update(locationstatus='BOOK')
    )()


async def Putaway_stage_1():
    pass


async def Putaway_stage_2():
    pass