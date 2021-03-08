# Generated by Django 3.0.11 on 2021-03-04 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeData',
            fields=[
                ('employeeid', models.IntegerField(db_column='EmployeeID', primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, db_column='Name', max_length=30, null=True)),
                ('surname', models.CharField(blank=True, db_column='Surname', max_length=50, null=True)),
            ],
            options={
                'db_table': 'EMPLOYEE_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HardwareData',
            fields=[
                ('hardwareid', models.CharField(db_column='HardwareID', max_length=8, primary_key=True, serialize=False)),
                ('hardwaretype', models.CharField(blank=True, db_column='HardwareType', max_length=1, null=True)),
                ('currentstage', models.SmallIntegerField(blank=True, db_column='CurrentStage', null=True)),
                ('isactive', models.BooleanField(blank=True, db_column='IsActive', null=True)),
            ],
            options={
                'db_table': 'HARDWARE_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ItemData',
            fields=[
                ('itemnumber', models.CharField(db_column='ItemNumber', max_length=20, primary_key=True, serialize=False)),
                ('itemname', models.CharField(blank=True, db_column='ItemName', max_length=500, null=True)),
                ('weightperpiece', models.FloatField(blank=True, db_column='WeightPerPiece', null=True)),
                ('amountperpallet', models.IntegerField(blank=True, db_column='AmountPerPallet', null=True)),
            ],
            options={
                'db_table': 'ITEM_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ItemGroupData',
            fields=[
                ('itemgroup', models.CharField(db_column='ItemGroup', max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, db_column='Name', max_length=100, null=True)),
                ('zone', models.CharField(blank=True, db_column='Zone', max_length=1, null=True)),
            ],
            options={
                'db_table': 'ITEM_GROUP_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='LayoutData',
            fields=[
                ('location', models.CharField(db_column='Location', max_length=30, primary_key=True, serialize=False)),
                ('locationtag', models.CharField(db_column='LocationTag', max_length=30)),
                ('description', models.CharField(blank=True, db_column='Description', max_length=500, null=True)),
                ('inventorystatus', models.CharField(blank=True, db_column='InventoryStatus', max_length=50, null=True)),
                ('locationstatus', models.CharField(blank=True, db_column='LocationStatus', max_length=3, null=True)),
                ('zone', models.CharField(blank=True, db_column='Zone', max_length=1, null=True)),
                ('row', models.CharField(blank=True, db_column='Row', max_length=2, null=True)),
                ('shelf', models.CharField(blank=True, db_column='Shelf', max_length=2, null=True)),
                ('position', models.CharField(blank=True, db_column='Position', max_length=2, null=True)),
            ],
            options={
                'db_table': 'LAYOUT_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='LogData',
            fields=[
                ('logid', models.IntegerField(db_column='LogID', primary_key=True, serialize=False)),
                ('logtype', models.CharField(blank=True, db_column='LogType', max_length=3, null=True)),
                ('errorfield', models.CharField(blank=True, db_column='ErrorField', max_length=20, null=True)),
                ('correctdata', models.CharField(blank=True, db_column='CorrectData', max_length=20, null=True)),
                ('stage', models.SmallIntegerField(blank=True, db_column='Stage', null=True)),
                ('scanpallet', models.CharField(blank=True, db_column='ScanPallet', max_length=30, null=True)),
                ('scanpalletweight', models.FloatField(blank=True, db_column='ScanPalletWeight', null=True)),
                ('scanlocation', models.CharField(blank=True, db_column='ScanLocation', max_length=30, null=True)),
                ('logtimestamp', models.DateTimeField(blank=True, db_column='LogTimestamp', null=True)),
            ],
            options={
                'db_table': 'LOG_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ModeData',
            fields=[
                ('mode', models.SmallIntegerField(db_column='Mode', primary_key=True, serialize=False)),
                ('description', models.CharField(blank=True, db_column='Description', max_length=30, null=True)),
                ('finalstage', models.SmallIntegerField(blank=True, db_column='FinalStage', null=True)),
            ],
            options={
                'db_table': 'MODE_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='OrderData',
            fields=[
                ('ordernumber', models.CharField(db_column='OrderNumber', max_length=20, primary_key=True, serialize=False)),
                ('ordereddatetime', models.DateTimeField(blank=True, db_column='OrderedDateTime', null=True)),
                ('invoicenumber', models.CharField(blank=True, db_column='InvoiceNumber', max_length=20, null=True)),
                ('invoicedatetime', models.DateTimeField(blank=True, db_column='InvoiceDateTime', null=True)),
                ('customerid', models.BigIntegerField(blank=True, db_column='CustomerID', null=True)),
                ('customername', models.CharField(blank=True, db_column='CustomerName', max_length=500, null=True)),
                ('customertype', models.CharField(blank=True, db_column='CustomerType', max_length=6, null=True)),
                ('province', models.CharField(blank=True, db_column='Province', max_length=250, null=True)),
                ('salesterritory', models.CharField(blank=True, db_column='SalesTerritory', max_length=6, null=True)),
                ('remarks', models.CharField(blank=True, db_column='Remarks', max_length=1000, null=True)),
                ('orderstatus', models.CharField(blank=True, db_column='OrderStatus', max_length=3, null=True)),
            ],
            options={
                'db_table': 'ORDER_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='OrderListData',
            fields=[
                ('orderlistid', models.IntegerField(db_column='OrderListID', primary_key=True, serialize=False)),
                ('quantity', models.IntegerField(blank=True, db_column='Quantity', null=True)),
                ('weight', models.FloatField(blank=True, db_column='Weight', null=True)),
                ('remainpickupquantity', models.IntegerField(blank=True, db_column='RemainPickupQuantity', null=True)),
            ],
            options={
                'db_table': 'ORDER_LIST_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PalletData',
            fields=[
                ('palletid', models.CharField(db_column='PalletID', max_length=30, primary_key=True, serialize=False)),
                ('amountofitem', models.IntegerField(blank=True, db_column='AmountOfItem', null=True)),
                ('amountavailable', models.IntegerField(blank=True, db_column='AmountAvailable', null=True)),
                ('palletweight', models.FloatField(blank=True, db_column='PalletWeight', null=True)),
                ('palletstatus', models.CharField(blank=True, db_column='PalletStatus', max_length=3, null=True)),
                ('putawaytimestamp', models.DateTimeField(blank=True, db_column='PutawayTimestamp', null=True)),
            ],
            options={
                'db_table': 'PALLET_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PickupData',
            fields=[
                ('pickupid', models.IntegerField(db_column='PickupID', primary_key=True, serialize=False)),
                ('quantity', models.IntegerField(blank=True, db_column='Quantity', null=True)),
                ('ispickup', models.BooleanField(blank=True, db_column='IsPickup', null=True)),
            ],
            options={
                'db_table': 'PICKUP_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PositionData',
            fields=[
                ('position', models.CharField(db_column='Position', max_length=3, primary_key=True, serialize=False)),
                ('description', models.CharField(blank=True, db_column='Description', max_length=100, null=True)),
            ],
            options={
                'db_table': 'POSITION_DATA',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='RfidTagData',
            fields=[
                ('rfidtag', models.CharField(db_column='RfidTag', max_length=30, primary_key=True, serialize=False)),
                ('attachtype', models.CharField(blank=True, db_column='AttachType', max_length=12, null=True)),
                ('code', models.CharField(blank=True, db_column='Code', max_length=30, null=True)),
            ],
            options={
                'db_table': 'RFID_TAG_DATA',
                'managed': False,
            },
        ),
    ]