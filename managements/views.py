from django.http import HttpResponse
from django.db.models import Q, F
from db.models import OrderData, OrderListData, PickupData, ItemData, PalletData, HardwareData
from modes.processes import commons
from asgiref.sync import async_to_sync
import json
import math


''' ***************************************************** '''
''' **************** MAIN FUNCTION PARTS **************** '''
''' ***************************************************** '''

''' Function of Order Receiving Management (ORM) '''
def Order_receiving_management(request):
    payload_json = json.loads((request.body).decode('utf-8'))

    order_list = payload_json['orders']

    # Store orders into database
    # Store_order_data(order_list)

    # Arrange pallet about how many rounds for pickup
    # Arrange_pallet()

    # Define hardware to respond pickup tasks
    # Define_hardware()

    # Notify to hardware about order coming for picking up
    Notify_order_coming()

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


''' Function for arranging pallet and defining pallet ID to each pickup record '''
def Arrange_pallet():

    # Get all order number which are not arranged
    order_numbers = list(OrderData.objects.filter(orderstatus='NO ARRANGE').values_list('ordernumber', flat=True))

    # Get all order list object which are not defined pallet
    order_list_records = list(OrderListData.objects.filter(ordernumber__in=order_numbers))

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

    # Access to each item number and amount of pallets
    for item_number in wanted_pallets_amount:
        
        # Get pallet ID list that match the item number and available amount is not 0, with LIMIT by the number of round (pallet)
        pallet_id_list = list(
            PalletData.objects.filter(itemnumber=item_number).exclude(amountavailable=0).values_list('palletid', flat=True).order_by('putawaytimestamp')[:wanted_pallets_amount[item_number]]
        )

        # Initialize pallet ID index that is unused
        pallet_id_used = 0

        # Define pallet ID to each pickup record
        for index, pickup_records_item in enumerate(pickup_records_items):
            if pickup_records_item == item_number:
                pickup_records[index].palletid_id = pallet_id_list[pallet_id_used]
                pallet_id_used = pallet_id_used + 1

        # Update available amount of each used pallet ID
        async_to_sync(commons.Update_multiple_pallets_info)(
            pallet_id_list=pallet_id_list,
            update_info_dict={'amountavailable': 0}
        )

    # Create multiple records in PICKUP_DATA
    PickupData.objects.bulk_create(pickup_records)


''' Function for defining hardware ID to pickup records which have to be picked up today '''
def Define_hardware():

    # Get all pickup record objects which wait for defining hardware and have due date today
    pickup_records = list(PickupData.objects.filter(
        pickupstatus='WAITHW',
        orderlistid__ordernumber__duedate=commons.Get_now_local_datetime().date()
    ))

    # Get all active hardware ID
    active_hardware_ids = list(HardwareData.objects.filter(isactive=True).values_list('hardwareid', flat=True))

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
def Notify_order_coming():

    # Get all hardware IDs which have to pick up items today
    hardware_ids = list(set(PickupData.objects.filter(pickupstatus='WAITPICK').values_list('hardwareid', flat=True)))

    # Access each hardware ID
    for hardware_id in hardware_ids:

        # Initialize data for sending to considered hardware ID with webapp payload
        data = []

        # Get pickup information of wanted records for sending to webapp, which have to be picked up today
        pickup_info = PickupData.objects.filter(
            orderlistid__ordernumber__duedate=commons.Get_now_local_datetime().date(),
            hardwareid=hardware_id
        ).annotate(
            order_number=F('orderlistid__ordernumber'),
            item_name=F('palletid__itemnumber__itemname'),
            location=F('palletid__location')
        ).values('order_number', 'pickupid', 'palletid', 'item_name', 'location', 'pickupstatus')

        # Get total pickip amount for today
        total_pickup = pickup_info.count()

        # Update data header
        for pickup in list(pickup_info):
            if pickup['pickupstatus'] == 'WAITPICK':
                data.append({
                    'order_number': pickup['order_number'],
                    'pickup_id': pickup['pickupid'],
                    'pickup_type': 'full',
                    'pallet_id': pickup['palletid'],
                    'item_name': pickup['item_name'],
                    'location': pickup['location']
                })

        # Generate payload for sending to webapp
        webapp_payload = commons.Payloads.m3s0(
            total_pickup=total_pickup,
            done_pickup=total_pickup - len(data),
            data=data
        )

        # Send payload to webapp
        async_to_sync(commons.Notify_clients)(
            hardware_id=hardware_id,
            webapp_payload=webapp_payload
        )
