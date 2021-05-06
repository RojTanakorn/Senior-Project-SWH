from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta
from django.utils import timezone


# Create your models here.
class HardwareData(models.Model):
    hardwareid = models.CharField(db_column='HardwareID', primary_key=True, max_length=8)  # Field name made lowercase.
    hardwaretype = models.CharField(db_column='HardwareType', max_length=1, blank=True, null=True)  # Field name made lowercase.
    currentmode = models.ForeignKey('ModeData', models.DO_NOTHING, db_column='CurrentMode', blank=True, null=True)  # Field name made lowercase.
    currentstage = models.SmallIntegerField(db_column='CurrentStage', blank=True, null=True)  # Field name made lowercase.
    isactive = models.BooleanField(db_column='IsActive', blank=True, null=True)  # Field name made lowercase.

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
    row = models.CharField(db_column='Row', max_length=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ITEM_GROUP_DATA'


class LayoutData(models.Model):
    location = models.CharField(db_column='Location', primary_key=True, max_length=30)  # Field name made lowercase.
    locationstatus = models.CharField(db_column='LocationStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    row = models.CharField(db_column='Row', max_length=2, blank=True, null=True)  # Field name made lowercase.
    shelf = models.CharField(db_column='Shelf', max_length=2, blank=True, null=True)  # Field name made lowercase.
    position = models.CharField(db_column='Position', max_length=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'LAYOUT_DATA'


class LocationTransferData(models.Model):
    locationtransferid = models.AutoField(db_column='LocationTransferID', primary_key=True)  # Field name made lowercase.
    palletid = models.ForeignKey('PalletData', models.DO_NOTHING, db_column='PalletID', blank=True, null=True)  # Field name made lowercase.
    sourcelocation = models.ForeignKey(LayoutData, models.DO_NOTHING, db_column='SourceLocation', blank=True, null=True, related_name='sourcelocation')  # Field name made lowercase.
    destinationlocation = models.ForeignKey(LayoutData, models.DO_NOTHING, db_column='DestinationLocation', blank=True, null=True, related_name='destinationlocation')  # Field name made lowercase.
    locationtransferstatus = models.CharField(db_column='LocationTransferStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    registertimestamp = models.DateTimeField(db_column='RegisterTimestamp', blank=True, null=True)  # Field name made lowercase.
    statustimestamp = models.DateTimeField(db_column='StatusTimestamp', blank=True, null=True)  # Field name made lowercase.
    hardwareid = models.ForeignKey(HardwareData, models.DO_NOTHING, db_column='HardwareID', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'LOCATION_TRANSFER_DATA'


class LogData(models.Model):
    logid = models.AutoField(db_column='LogID', primary_key=True)  # Field name made lowercase.
    logtype = models.CharField(db_column='LogType', max_length=3, blank=True, null=True)  # Field name made lowercase.
    errorfield = models.CharField(db_column='ErrorField', max_length=20, blank=True, null=True)  # Field name made lowercase.
    mode = models.ForeignKey('ModeData', models.DO_NOTHING, db_column='Mode', blank=True, null=True)  # Field name made lowercase.
    stage = models.SmallIntegerField(db_column='Stage', blank=True, null=True)  # Field name made lowercase.
    scanpallet = models.CharField(db_column='ScanPallet', max_length=30, blank=True, null=True)  # Field name made lowercase.
    scanpalletweight = models.FloatField(db_column='ScanPalletWeight', blank=True, null=True)  # Field name made lowercase.
    scanlocation = models.CharField(db_column='ScanLocation', max_length=30, blank=True, null=True)  # Field name made lowercase.
    employeeid = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, db_column='EmployeeID', blank=True, null=True)  # Field name made lowercase.
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
    customerid = models.IntegerField(db_column='CustomerID', blank=True, null=True)  # Field name made lowercase.
    remarks = models.CharField(db_column='Remarks', max_length=1000, blank=True, null=True)  # Field name made lowercase.
    orderstatus = models.CharField(db_column='OrderStatus', max_length=10, blank=True, null=True)  # Field name made lowercase.
    duedate = models.DateField(db_column='DueDate', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ORDER_DATA'


class OrderListData(models.Model):
    orderlistid = models.AutoField(db_column='OrderListID', primary_key=True)  # Field name made lowercase.
    ordernumber = models.ForeignKey(OrderData, models.DO_NOTHING, db_column='OrderNumber', blank=True, null=True)  # Field name made lowercase.
    itemnumber = models.ForeignKey(ItemData, models.DO_NOTHING, db_column='ItemNumber', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(db_column='Quantity', blank=True, null=True)  # Field name made lowercase.
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


class UserData(models.Model):
    userid = models.OneToOneField(User, db_column='UserID', on_delete=models.CASCADE, primary_key=True)  # Field name made lowercase.
    currentmode = models.ForeignKey(ModeData, models.DO_NOTHING, db_column='CurrentMode', blank=True, null=True)  # Field name made lowercase.
    currentstage = models.SmallIntegerField(db_column='CurrentStage', blank=True, null=True)  # Field name made lowercase.
    ison = models.BooleanField(db_column='IsOn', blank=True, null=True)  # Field name made lowercase.
    hardwareid = models.ForeignKey(HardwareData, models.DO_NOTHING, db_column='HardwareID', blank=True, null=True)  # Field name made lowercase.
    userimagepath = models.ImageField(upload_to='user_images', db_column='UserImagePath', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'USER_DATA'

    def __str__(self):
        return self.userid.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserData.objects.create(userid=instance, currentmode_id=0, currentstage=0, ison=False)