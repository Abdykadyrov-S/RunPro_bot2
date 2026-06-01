from django.db import models


class Driver(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    chat_id = models.BigIntegerField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "drivers"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name or f"Driver {self.id}"


class Dispatcher(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    telegram_user_id = models.BigIntegerField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "dispatchers"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name or f"Dispatcher {self.id}"


class Load(models.Model):
    id = models.AutoField(primary_key=True)
    driver = models.ForeignKey(Driver, models.DO_NOTHING, db_column="driver_id", blank=True, null=True)
    dispatcher = models.ForeignKey(Dispatcher, models.DO_NOTHING, db_column="dispatcher_id", blank=True, null=True)
    broker = models.TextField(blank=True, null=True)
    load_number = models.TextField(unique=True, blank=True, null=True)
    rate = models.FloatField(blank=True, null=True)
    miles = models.FloatField(blank=True, null=True)
    pu_date = models.TextField(blank=True, null=True)
    del_date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "loads"
        ordering = ["-id"]

    def __str__(self):
        return self.load_number or f"Load {self.id}"


class Chat(models.Model):
    chat_id = models.BigIntegerField(primary_key=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "chats"
        ordering = ["title", "chat_id"]

    def __str__(self):
        return self.title or str(self.chat_id)
