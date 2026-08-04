"""Compatibility node required by migration 0010.

The distributed local copy lost this historical file. Restoring the node keeps
Django's migration graph consistent without deleting or recreating data.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_landinglead"),
    ]

    operations = []
