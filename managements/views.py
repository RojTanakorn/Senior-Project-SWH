from django.http import HttpResponse
from django.db.models import Q
from db.models import OrderData, OrderListData, PickupData, ItemData, PalletData, HardwareData
import json
import math

# Create your views here.
def Order_receiving_management(request):
    payload_json = json.loads((request.body).decode('utf-8'))

    order_list = payload_json['orders']

    Store_order_data(order_list)

    Arrange_pallet()

    Define_hardware()

    # ** Notify_order_coming()

    order_numbers = list(
        PickupData.objects.filter(pickupstatus='WAITPICK', duedate=).values_list('ordernumber', flat=True)
    )


    return HttpResponse('Done')


def Store_order_data(order_list):
    order_records = []
    order_list_records = []

    for order in order_list:
        order_records.append(
            OrderData(
                ordernumber=order['order_number'],
                customerid=order['customer_id'],
                duedate=order['due_date'],
                orderstatus='NO ARRANGE'
            )
        )

        for item in order['item_list']:
            order_list_records.append(
                OrderListData(
                    ordernumber_id=order['order_number'],
                    itemnumber_id=item['item_number'],
                    quantity=item['quantity'],
                    remainpickupquantity=item['quantity']
                )
            )
    
    OrderData.objects.bulk_create(order_records)
    OrderListData.objects.bulk_create(order_list_records)


def Arrange_pallet():

    order_numbers = list(OrderData.objects.filter(orderstatus='NO ARRANGE').values_list('ordernumber', flat=True))

    order_list_records = list(OrderListData.objects.filter(ordernumber__in=order_numbers))

    pickup_records = []
    pickup_records_items = []

    item_numbers = list(set(order_list_record.itemnumber_id for order_list_record in order_list_records))
    wanted_pallets_amount = dict(zip(item_numbers, [0] * len(item_numbers)))

    results = list(ItemData.objects.filter(itemnumber__in=item_numbers).values('itemnumber', 'amountperpallet'))

    for order_list_record in order_list_records:

        item_number = order_list_record.itemnumber_id
        quantity = order_list_record.quantity

        amount_per_pallet = next((result['amountperpallet'] for result in results if result['itemnumber'] == item_number), None)

        pickup_round = math.ceil(quantity / amount_per_pallet)

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

        wanted_pallets_amount[item_number] = wanted_pallets_amount[item_number] + pickup_round

    print(wanted_pallets_amount)

    for item_number in wanted_pallets_amount:

        pallet_id_list = list(
            PalletData.objects.filter(itemnumber=item_number).values_list('palletid', flat=True).order_by('putawaytimestamp')[:wanted_pallets_amount[item_number]]
        )

        print(pallet_id_list)

        pallet_id_used = 0

        for index, pickup_records_item in enumerate(pickup_records_items):
            if pickup_records_item == item_number:
                pickup_records[index].palletid_id = pallet_id_list[pallet_id_used]
                pallet_id_used = pallet_id_used + 1

    PickupData.objects.bulk_create(pickup_records)


def Define_hardware():
    pickup_records = list(PickupData.objects.filter(pickupstatus='WAITHW'))

    active_hardware_ids = list(HardwareData.objects.filter(isactive=True).values_list('hardwareid', flat=True))

    hardware_id_loop_index = 0

    for pickup_count in range(len(pickup_records)):
        pickup_records[pickup_count].hardwareid_id = active_hardware_ids[hardware_id_loop_index]
        pickup_records[pickup_count].pickupstatus = 'WAITPICK'
        hardware_id_loop_index = hardware_id_loop_index + 1

        if hardware_id_loop_index >= len(active_hardware_ids):
            hardware_id_loop_index = 0

    PickupData.objects.bulk_update(pickup_records, ['pickupstatus', 'hardwareid'])
