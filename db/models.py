from django.db import models

# Create your models here.
class EmployeeData(models.Model):
    employeeid = models.AutoField(db_column='EmployeeID', primary_key=True)  # Field name made lowercase.
    name = models.CharField(db_column='Name', max_length=30, blank=True, null=True)  # Field name made lowercase.
    surname = models.CharField(db_column='Surname', max_length=50, blank=True, null=True)  # Field name made lowercase.
    position = models.ForeignKey('PositionData', models.DO_NOTHING, db_column='Position', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EMPLOYEE_DATA'


class HardwareData(models.Model):
    hardwareid = models.CharField(db_column='HardwareID', primary_key=True, max_length=8)  # Field name made lowercase.
    hardwaretype = models.CharField(db_column='HardwareType', max_length=1, blank=True, null=True)  # Field name made lowercase.
    currentmode = models.ForeignKey('ModeData', models.DO_NOTHING, db_column='CurrentMode', blank=True, null=True)  # Field name made lowercase.
    currentstage = models.SmallIntegerField(db_column='CurrentStage', blank=True, null=True)  # Field name made lowercase.
    isactive = models.BooleanField(db_column='IsActive', blank=True, null=True)  # Field name made lowercase.
    employeeid = models.ForeignKey(EmployeeData, models.DO_NOTHING, db_column='EmployeeID', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'HARDWARE_DATA'


class ItemData(models.Model):
    itemnumber = models.CharField(db_column='ItemNumber', primary_key=True, max_length=20)  # Field name made lowercase.
    itemname = models.CharField(db_column='ItemName', max_length=500, blank=True, null=True)  # Field name made lowercase.
    weightperpiece = models.FloatField(db_column='WeightPerPiece', blank=True, null=True)  # Field name made lowercase.
    itemgroup = models.ForeignKey('ItemGroupData', models.DO_NOTHING, db_column='ItemGroup', blank=True, null=True)  # Field name made lowercase.
    amountperpallet = models.IntegerField(db_column='AmountPerPallet', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ITEM_DATA'


class ItemGroupData(models.Model):
    itemgroup = models.CharField(db_column='ItemGroup', primary_key=True, max_length=50)  # Field name made lowercase.
    name = models.CharField(db_column='Name', max_length=100, blank=True, null=True)  # Field name made lowercase.
    zone = models.CharField(db_column='Zone', max_length=1, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ITEM_GROUP_DATA'


class LayoutData(models.Model):
    location = models.CharField(db_column='Location', primary_key=True, max_length=30)  # Field name made lowercase.
    locationtag = models.CharField(db_column='LocationTag', max_length=30, blank=True, null=True)  # Field name made lowercase.
    description = models.CharField(db_column='Description', max_length=500, blank=True, null=True)  # Field name made lowercase.
    inventorystatus = models.CharField(db_column='InventoryStatus', max_length=50, blank=True, null=True)  # Field name made lowercase.
    locationstatus = models.CharField(db_column='LocationStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    zone = models.CharField(db_column='Zone', max_length=1, blank=True, null=True)  # Field name made lowercase.
    row = models.CharField(db_column='Row', max_length=2, blank=True, null=True)  # Field name made lowercase.
    shelf = models.CharField(db_column='Shelf', max_length=2, blank=True, null=True)  # Field name made lowercase.
    position = models.CharField(db_column='Position', max_length=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'LAYOUT_DATA'


class LogData(models.Model):
    logid = models.AutoField(db_column='LogID', primary_key=True)  # Field name made lowercase.
    logtype = models.CharField(db_column='LogType', max_length=3, blank=True, null=True)  # Field name made lowercase.
    errorfield = models.CharField(db_column='ErrorField', max_length=20, blank=True, null=True)  # Field name made lowercase.
    correctdata = models.CharField(db_column='CorrectData', max_length=20, blank=True, null=True)  # Field name made lowercase.
    mode = models.ForeignKey('ModeData', models.DO_NOTHING, db_column='Mode', blank=True, null=True)  # Field name made lowercase.
    stage = models.SmallIntegerField(db_column='Stage', blank=True, null=True)  # Field name made lowercase.
    scanpallet = models.CharField(db_column='ScanPallet', max_length=30, blank=True, null=True)  # Field name made lowercase.
    scanpalletweight = models.FloatField(db_column='ScanPalletWeight', blank=True, null=True)  # Field name made lowercase.
    scanlocation = models.CharField(db_column='ScanLocation', max_length=30, blank=True, null=True)  # Field name made lowercase.
    employeeid = models.ForeignKey(EmployeeData, models.DO_NOTHING, db_column='EmployeeID', blank=True, null=True)  # Field name made lowercase.
    logtimestamp = models.DateTimeField(db_column='LogTimestamp', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'LOG_DATA'


class ModeData(models.Model):
    mode = models.SmallIntegerField(db_column='Mode', primary_key=True)  # Field name made lowercase.
    description = models.CharField(db_column='Description', max_length=500, blank=True, null=True)  # Field name made lowercase.
    finalstage = models.SmallIntegerField(db_column='FinalStage', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MODE_DATA'


class OrderData(models.Model):
    ordernumber = models.CharField(db_column='OrderNumber', primary_key=True, max_length=20)  # Field name made lowercase.
    ordereddatetime = models.DateTimeField(db_column='OrderedDateTime', blank=True, null=True)  # Field name made lowercase.
    invoicenumber = models.CharField(db_column='InvoiceNumber', max_length=20, blank=True, null=True)  # Field name made lowercase.
    invoicedatetime = models.DateTimeField(db_column='InvoiceDateTime', blank=True, null=True)  # Field name made lowercase.
    customerid = models.BigIntegerField(db_column='CustomerID', blank=True, null=True)  # Field name made lowercase.
    customername = models.CharField(db_column='CustomerName', max_length=500, blank=True, null=True)  # Field name made lowercase.
    customertype = models.CharField(db_column='CustomerType', max_length=6, blank=True, null=True)  # Field name made lowercase.
    province = models.CharField(db_column='Province', max_length=250, blank=True, null=True)  # Field name made lowercase.
    salesterritory = models.CharField(db_column='SalesTerritory', max_length=6, blank=True, null=True)  # Field name made lowercase.
    remarks = models.CharField(db_column='Remarks', max_length=1000, blank=True, null=True)  # Field name made lowercase.
    orderstatus = models.CharField(db_column='OrderStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ORDER_DATA'


class OrderListData(models.Model):
    orderlistid = models.AutoField(db_column='OrderListID', primary_key=True)  # Field name made lowercase.
    ordernumber = models.ForeignKey(OrderData, models.DO_NOTHING, db_column='OrderNumber', blank=True, null=True)  # Field name made lowercase.
    itemnumber = models.ForeignKey(ItemData, models.DO_NOTHING, db_column='ItemNumber', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(db_column='Quantity', blank=True, null=True)  # Field name made lowercase.
    weight = models.FloatField(db_column='Weight', blank=True, null=True)  # Field name made lowercase.
    remainpickupquantity = models.IntegerField(db_column='RemainPickupQuantity', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ORDER_LIST_DATA'


class PalletData(models.Model):
    palletid = models.CharField(db_column='PalletID', primary_key=True, max_length=30)  # Field name made lowercase.
    itemnumber = models.ForeignKey(ItemData, models.DO_NOTHING, db_column='ItemNumber', blank=True, null=True)  # Field name made lowercase.
    amountofitem = models.IntegerField(db_column='AmountOfItem', blank=True, null=True)  # Field name made lowercase.
    amountavailable = models.IntegerField(db_column='AmountAvailable', blank=True, null=True)  # Field name made lowercase.
    palletweight = models.FloatField(db_column='PalletWeight', blank=True, null=True)  # Field name made lowercase.
    palletstatus = models.CharField(db_column='PalletStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    location = models.ForeignKey(LayoutData, models.DO_NOTHING, db_column='Location', blank=True, null=True)  # Field name made lowercase.
    putawaytimestamp = models.DateTimeField(db_column='PutawayTimestamp', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'PALLET_DATA'


class PickupData(models.Model):
    pickupid = models.AutoField(db_column='PickupID', primary_key=True)  # Field name made lowercase.
    orderlistid = models.ForeignKey(OrderListData, models.DO_NOTHING, db_column='OrderListID', blank=True, null=True)  # Field name made lowercase.
    palletid = models.ForeignKey(PalletData, models.DO_NOTHING, db_column='PalletID', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(db_column='Quantity', blank=True, null=True)  # Field name made lowercase.
    pickupstatus = models.CharField(db_column='PickupStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    hardwareid = models.ForeignKey(HardwareData, models.DO_NOTHING, db_column='HardwareID', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'PICKUP_DATA'


class PositionData(models.Model):
    position = models.CharField(db_column='Position', primary_key=True, max_length=3)  # Field name made lowercase.
    description = models.CharField(db_column='Description', max_length=100, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'POSITION_DATA'


class RfidTagData(models.Model):
    rfidtag = models.CharField(db_column='RfidTag', primary_key=True, max_length=30)  # Field name made lowercase.
    attachtype = models.CharField(db_column='AttachType', max_length=12, blank=True, null=True)  # Field name made lowercase.
    code = models.CharField(db_column='Code', max_length=30, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'RFID_TAG_DATA'