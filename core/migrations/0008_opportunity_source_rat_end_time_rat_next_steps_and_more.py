"""Compatibility node for the historical 0008 branch.

This package restores the migration graph used by the official MGT 1.0
repository. Database changes represented by this historical node are already
reflected by the current database/model state, so no destructive operation is
performed here.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_opportunity_client_and_more"),
    ]

    operations = []
