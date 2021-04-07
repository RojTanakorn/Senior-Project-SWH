from django.http import HttpResponse
from db.models import PalletData, HardwareData, LayoutData, LocationTransferData
from modes.processes import commons
from asgiref.sync import async_to_sync
import json


''' Function of Location Transfer Management '''
def Location_transfer_management(request):
    payload_json = json.loads((request.body).decode('utf-8'))

    source_location = payload_json['source_location']
    destination_location = payload_json['destination_location']

    error_messages = []

    # ======= Verify source location =======
    source_status = LayoutData.objects.filter(location=source_location).values_list('locationstatus', flat=True).first()

    if source_status is None:
        error_messages.append('ไม่มีชั้นวางต้นทางหมายเลขนี้')

    elif source_status != 'BUSY':
        error_messages.append(f'ชั้นวางต้นทางไม่มีสินค้าวาง ถูกจอง หรือรอการตรวจสอบ [status: {source_status}]')

    else:
        source_info = PalletData.objects.filter(location=source_location).values('palletid', 'palletstatus').first()

        if source_info['palletstatus'] != 'GENERAL':
            error_messages.append("สินค้าไม่พร้อมสำหรับเคลื่อนย้าย.")


    # # ======= Verify destination location =======
    # destination_location_status = LayoutData.objects.filter(location=destination_location).values_list('locationstatus', flat=True)

    # if destination_location_status != 'BLANK':
    #     error_messages.append("ชั้นวางไม่พร้อมสำหรับวางสินค้า. (ไม่ว่างหรือถูกจอง)")

    
    # if len(error_messages) != 0:
    #     error_text = "ERROR: " + (', '.join(error_messages))
    #     return HttpResponse(error_text)

    # else:
    #     LayoutData.objects.filter(location=destination_location).update(locationstatus='BOOK')

    #     # Get all active hardware ID
    #     active_hardware_ids = list(HardwareData.objects.filter(isactive=True).values_list('hardwareid', flat=True))

    #     LocationTransferData.objects.filter(
    #         registertimestamp__date=commons.Get_now_local_datetime().date()
    #     )
    return HttpResponse(error_messages)
    # 1. receive request
    # 2. check source location has pallet?
    # 3. check destination location is BLANK?
    # 4. book destination location
    # 5. Assign task to hardware
    # 6. Notify hardware
    # 7. store location transfer task into LOCATION_TRANSFER_DATA