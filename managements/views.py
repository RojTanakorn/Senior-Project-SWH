from django.http import HttpResponse, JsonResponse
from db.models import PalletData, HardwareData, LayoutData, LocationTransferData
from modes.processes import commons
from asgiref.sync import async_to_sync
import json
from django.db.models import Count


''' Function of Location Transfer Management '''
def Location_transfer_management(request):

    # Get payload as JSON
    payload_json = json.loads((request.body).decode('utf-8'))

    # Extract data to source location and destination location
    source_location = payload_json['source_location']
    destination_location = payload_json['destination_location']

    # Initialize list of error
    error_messages = []


    # ======= Verify source location =======
    # Get location status of source location
    source_location_status = LayoutData.objects.filter(location=source_location).values_list('locationstatus', flat=True).first()

    # Check if source location doesn't exist
    if source_location_status is None:
        error_messages.append('ไม่มีชั้นวางต้นทางหมายเลขนี้')

    # Check if source location doesn't place pallet
    elif source_location_status != 'BUSY':
        error_messages.append(f'ชั้นวางต้นทางไม่พร้อมสำหรับให้เคลื่อนย้าย เนื่องจากชั้นวางต้นทางมีสถานะ [{source_location_status}]')

    else:

        # Get pallet id and pallet status of pallet stored in source location
        pallet_info = PalletData.objects.filter(location=source_location).values_list('palletid', 'palletstatus').first()

        # Check if no pallet is stored in source location
        if pallet_info is None:
            error_messages.append('ไม่มีพาเลทวางอยู่บนชั้นวางต้นทางในฐานข้อมูล')

        else:
            pallet_id, pallet_status = pallet_info
            
            # Check if pallet is not ready to move
            if pallet_status != 'GENERAL':
                error_messages.append(f'พาเลทที่วางอยู่บนชั้นวางต้นทางไม่สามารถเคลื่อนย้ายได้ เนื่องจากพาเลทมีสถานะ [{pallet_status}]')


    # ======= Verify destination location =======
    # Get location status of destination location
    destination_location_status = LayoutData.objects.filter(location=destination_location).values_list('locationstatus', flat=True).first()

    # Check if destination location doesn't exist
    if destination_location_status is None:
        error_messages.append('ไม่มีชั้นวางปลายทางหมายเลขนี้')

    # Check if source location is not BLANK
    elif destination_location_status != 'BLANK':
        error_messages.append(f'ชั้นวางปลายทางไม่พร้อมสำหรับวางพาเลท เนื่องจากชั้นวางปลายทางมีสถานะ [{destination_location_status}]')

    else:

        # **check for sure that no pallet stored in destination location
        is_pallet_stored = PalletData.objects.filter(location=destination_location).exists()

        if is_pallet_stored:
            error_messages.append('ชั้นวางปลายทางไม่พร้อมสำหรับวางพาเลท เนื่องจากชั้นวางปลายทางมีพาเลทวางอยู่ในฐานข้อมูล')


    # ======= Handle order of location transfer if there is no error =======
    if len(error_messages) == 0:

        # Get all active hardware ID
        active_hardware_ids = list(HardwareData.objects.filter(isactive=True).values_list('hardwareid', flat=True))
        
        # Get count of each hardware's tasks today
        today_hardware_tasks = list(LocationTransferData.objects.filter(
            registertimestamp__date=commons.Get_now_local_datetime().date(),
            hardwareid__in=active_hardware_ids
        ).values('hardwareid').annotate(today_task=Count('hardwareid')).order_by('today_task'))

        # Check if some hardwares are not assigned to do location transfer task today
        if len(today_hardware_tasks) < len(active_hardware_ids):

            # Get hardware IDs that have already been assigned today
            today_hardwares = set([task['hardwareid'] for task in today_hardware_tasks])

            # Assign a task to the first hardware ID that is not assigned today
            assigned_hardware_id = list(set(active_hardware_ids).difference(today_hardwares))[0]

        else:

            # Assign a task to the first hardware ID who has the lowest number of tasks compared to other hardwares
            assigned_hardware_id = today_hardware_tasks[0]['hardwareid']

        # Store location transfer order into LOCATION_TRANSFER_DATA
        LocationTransferData.objects.create(
            palletid_id=pallet_id,
            sourcelocation_id=source_location,
            destinationlocation_id=destination_location,
            locationtransferstatus='WAITMOVE',
            registertimestamp=commons.Get_now_local_datetime(),
            hardwareid_id=assigned_hardware_id
        )

        # Book destination location for location transfer on LAYOUT_DATA
        LayoutData.objects.filter(location=destination_location).update(locationstatus='BOOK')

        # Change pallet status to be WAITMOVE on PALLET_DATA
        PalletData.objects.filter(palletid=pallet_id).update(palletstatus='WAITMOVE')

        # Send payload to webapp for notifying coming task
        async_to_sync(commons.Notify_clients)(
            hardware_id=assigned_hardware_id, webapp_payload=commons.Payloads.m4s1()
        )


    return JsonResponse({'error': error_messages})