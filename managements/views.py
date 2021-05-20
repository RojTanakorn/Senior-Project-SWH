from django.http import HttpResponse, JsonResponse
from db.models import OrderData, OrderListData, PickupData, ItemData, PalletData, HardwareData, LayoutData, LocationTransferData, UserData
from modes.processes import commons
from asgiref.sync import async_to_sync
import json
import math
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from authen.views import ExpiringTokenAuthenticationClass
from rest_framework import permissions


''' ***************************************************** '''
''' **************** MAIN FUNCTION PARTS **************** '''
''' ***************************************************** '''

''' Function of Order Receiving Management (ORM) '''
def Order_receiving_management(request):
    payload_json = json.loads((request.body).decode('utf-8'))

    order_list = payload_json['orders']

    # Store orders into database
    Store_order_data(order_list)

    # Arrange pallet about how many rounds for pickup
    Arrange_pallet()

    # Define hardware to respond pickup tasks
    Define_hardware()

    # Notify to hardware about order coming for picking up
    Notify_all_pickup_coming()

    return HttpResponse('Done')


''' ********************************************************** '''
''' **************** STAGE SUB FUNCTIONS PART **************** '''
''' ********************************************************** '''

''' Function for storing order data and order list data '''
def Store_order_data(order_list):

    # Initialize list of:
    #   - order records --> into ORDER_DATA
    #   - order list records --> into ORDER_LIST_DATA
    order_records = []
    order_list_records = []

    # access each order
    for order in order_list:

        # Append order record into order records
        order_records.append(
            OrderData(
                ordernumber=order['order_number'],
                customerid=order['customer_id'],
                duedate=order['due_date'],
                orderstatus='NO ARRANGE'
            )
        )

        # access each item which is ordered
        for item in order['item_list']:

            # Append order list record into order list records
            order_list_records.append(
                OrderListData(
                    ordernumber_id=order['order_number'],
                    itemnumber_id=item['item_number'],
                    quantity=item['quantity'],
                    remainpickupquantity=item['quantity']
                )
            )
    
    # Create multiple records in ORDER_DATA and ORDER_LIST_DATA
    OrderData.objects.bulk_create(order_records)
    OrderListData.objects.bulk_create(order_list_records)


''' Function for arranging pallet and defining pallet ID to each pickup record (only have to be picked up that day) '''
def Arrange_pallet():

    # =========== Separate order list to pickup record part ===========
    # Get all order number which are not arranged and have to be picked up today
    today_order_numbers = list(
        OrderData.objects.filter(
            orderstatus='NO ARRANGE',
            duedate=commons.Get_now_local_datetime().date()
        ).values_list('ordernumber', flat=True)
    )

    # Get all order list object which are not defined pallet
    order_list_records = list(OrderListData.objects.filter(ordernumber__in=today_order_numbers))

    # Initialize pickup records for storing into PICKUP_DATA, pickup records items is about item number according to pickup records (same index)
    pickup_records = []
    pickup_records_items = []

    # Get item number in order list object uniquely
    item_numbers = list(set(order_list_record.itemnumber_id for order_list_record in order_list_records))

    # Initial dict for mapping item number and wanted pallet amount ==> ex. '<item_number>': wanted amount
    wanted_pallets_amount = dict(zip(item_numbers, [0] * len(item_numbers)))

    # Get amount per pallet of each wanted item number
    items = async_to_sync(commons.Get_multiple_items_info)(
        item_number_list=item_numbers,
        wanted_fields=('itemnumber', 'amountperpallet')
    )

    # Access each order list record
    for order_list_record in order_list_records:

        # Extract some datas of order list record
        item_number = order_list_record.itemnumber_id
        quantity = order_list_record.quantity

        # Get amount per pallet of considered item number
        amount_per_pallet = next((item['amountperpallet'] for item in items if item['itemnumber'] == item_number), None)

        # Calcualate the number of round (pallet) for picking up this item number
        pickup_round = math.ceil(quantity / amount_per_pallet)

        # Create pickup record object according to the number of round
        if pickup_round == 1:
            pickup_records.append(PickupData(
                orderlistid_id=order_list_record.orderlistid,
                quantity=amount_per_pallet,
                pickupstatus='WAITHW'
            ))

            pickup_records_items.append(item_number)

        else:
            for _ in range(pickup_round):
                pickup_records.append(PickupData(
                    orderlistid_id=order_list_record.orderlistid,
                    quantity=amount_per_pallet,
                    pickupstatus='WAITHW'
                ))

                pickup_records_items.append(item_number)

        # Update the number of round of considered item number
        wanted_pallets_amount[item_number] = wanted_pallets_amount[item_number] + pickup_round

    # =========== Define pallet ID to each pickup record part ===========
    # Access to each item number and amount of pallets
    for item_number in wanted_pallets_amount:
        
        # Get pallet ID list that match the item number and available amount is not 0, with LIMIT by the number of round (pallet)
        pallet_id_list = list(
            PalletData.objects.filter(
                itemnumber=item_number,
                palletstatus='GENERAL'
            ).values_list('palletid', flat=True).order_by('putawaytimestamp')[:wanted_pallets_amount[item_number]]
        )

        # Initialize pallet ID index that is unused
        pallet_id_used = 0

        # Define pallet ID to each pickup record
        for index, pickup_records_item in enumerate(pickup_records_items):
            if pickup_records_item == item_number:
                pickup_records[index].palletid_id = pallet_id_list[pallet_id_used]
                pallet_id_used = pallet_id_used + 1

        # Update available amount and pallet status of each used pallet ID
        async_to_sync(commons.Update_multiple_pallets_info)(
            pallet_id_list=pallet_id_list,
            update_info_dict={'palletstatus': 'WAITPICK', 'amountavailable': 0}
        )

    # Create multiple records in PICKUP_DATA
    PickupData.objects.bulk_create(pickup_records)

    # Update order number status
    OrderData.objects.filter(ordernumber__in=today_order_numbers).update(orderstatus='WAITPICK')


''' Function for defining hardware ID to pickup records which have to be picked up today '''
def Define_hardware():

    # Get all pickup record objects which wait for defining hardware and have due date today
    pickup_records = list(PickupData.objects.filter(pickupstatus='WAITHW'))

    # Get all active hardware ID
    active_hardware_ids = list(UserData.objects.filter(ison=True, hardwareid__isnull=False).values_list('hardwareid', flat=True))

    # Initialize hardware ID index for spreading tasks
    hardware_id_index = 0

    # Update pickup status and define hardware ID
    for pickup_count in range(len(pickup_records)):
        pickup_records[pickup_count].hardwareid_id = active_hardware_ids[hardware_id_index]
        pickup_records[pickup_count].pickupstatus = 'WAITPICK'
        hardware_id_index = hardware_id_index + 1

        if hardware_id_index >= len(active_hardware_ids):
            hardware_id_index = 0

    # Update multiple pickup records about pickup status and hardware ID
    PickupData.objects.bulk_update(pickup_records, ['pickupstatus', 'hardwareid'])


''' Function for notifying webapp about coming pickup orders for today '''
def Notify_all_pickup_coming():

    # Get all hardware IDs which have to pick up items today
    hardware_ids = list(set(PickupData.objects.filter(pickupstatus='WAITPICK').values_list('hardwareid', flat=True)))

    webapp_payload = commons.Payloads.m3s1()
    # Access each hardware ID
    for hardware_id in hardware_ids:

        async_to_sync(commons.Notify_clients)(
            hardware_id=hardware_id,
            webapp_payload=webapp_payload
        )


class Location_transfer_management(APIView):
    
    authentication_classes = [ExpiringTokenAuthenticationClass]
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
         # Extract data to source location and destination location from params
        source_location = request.GET.get('source', '')
        destination_location = request.GET.get('destination', '')

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
            active_hardware_ids = list(UserData.objects.filter(ison=True, hardwareid__isnull=False).values_list('hardwareid', flat=True))

            if len(active_hardware_ids) == 0:
                error_messages.append('ไม่มีฮาร์ดแวร์ที่ทำงานอยู่ ณ ขณะนี้')

            else:
            
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

        return Response({'error': error_messages})