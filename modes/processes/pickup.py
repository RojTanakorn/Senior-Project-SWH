from channels.db import database_sync_to_async
from . import commons
from django.db.models import F
from db.models import PickupData, PalletData


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
        error_type=error_type
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

    verify_pickup_amount_status, error_type = await Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id)

    if verify_pickup_amount_status:

        # Get remained data for pickup
        pass

    # Store log into LOG_DATA
    # await commons.Store_log(
    #     create_log_dict={
    #         'logtype': 'GEN' if verify_pickup_amount_status else 'ERR',
    #         'errorfield': error_type,
    #         'mode_id': 3,
    #         'stage': 2,
    #         'scanpallet': scanned_pallet_id,
    #         'scanpalletweight': scanned_pallet_weight,
    #         'employeeid_id': employee_id,
    #         'logtimestamp': commons.Get_now_local_datetime()
    #     }
    # )

    # Generate payload for sending to clients (hardware and webapp)
    # hardware_payload, webapp_payload = commons.Payloads.m3s2()

    # Send payload to clients
    # await commons.Notify_clients(
    #     hardware_id=hardware_id,
    #     hardware_payload=hardware_payload,
    #     webapp_payload=webapp_payload
    # )


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

async def Verify_pickup_pallet(scanned_pallet_id, scanned_location, hardware_id):

    # Initialize status and error type
    verify_pickup_pallet_status = False
    error_type = None

    # Check that employee go to correct pallet & location or not
    results = await database_sync_to_async(
        lambda: list(PickupData.objects.filter(palletid=scanned_pallet_id, pickupstatus='WAITPICK').annotate(
                    location=F('palletid__location')
                ).values('pickupid', 'hardwareid', 'location'))
    )()

    if len(results) == 0:

        # This pallet is not for picking up
        error_type = 'NOT FOR PICK'

    else:
        pickup_record = results[0]
        if pickup_record['hardwareid'] != hardware_id:

            # This task is not your job
            error_type = 'NOT YOUR TASK'

        else:
            if pickup_record['location'] != scanned_location:

                # This pallet is at wrong location, someone moved it
                error_type = 'LOCATION'

            else:

                # This job is correct
                verify_pickup_pallet_status = True

                # Update pickup record status
                await database_sync_to_async(
                    lambda: PickupData.objects.filter(pickupid=pickup_record['pickupid']).update(pickupstatus='PICKING')
                )()
    
    return verify_pickup_pallet_status, error_type


async def Verify_pickup_amount(scanned_pallet_id, scanned_pallet_weight, hardware_id):

    # Initialize status and error type
    verify_pickup_amount_status = False
    error_type = None


    results = await database_sync_to_async(
        lambda: list(PickupData.objects.filter(palletid=scanned_pallet_id, pickupstatus='PICKING').values(
            'pickupid', 'quantity', 'hardwareid'
        ))
    )()

    if len(results) == 0:
        
        # Employee didn't do a considered pallet from stage 1
        error_type = 'WRONG PALLET'

    else:
        pickup_record = results[0]

        if pickup_record['hardwareid'] != hardware_id:

            # This task is not your job
            error_type = 'NOT YOUR TASK'

        else:

            # Verify weight of pallet
            expected_pallet_weight = await database_sync_to_async(
                lambda: PalletData.objects.filter(palletid=scanned_pallet_id).values_list('palletweight', flat=True)
            )()

            min_weight = (1 - commons.PALLET_WEIGHT_ERROR) * expected_pallet_weight
            max_weight = (1 + commons.PALLET_WEIGHT_ERROR) * expected_pallet_weight

            if min_weight <= scanned_pallet_weight <= max_weight:
                verify_pickup_amount_status = True
            else:
                error_type = 'AMOUNT'

    return verify_pickup_amount_status, error_type



