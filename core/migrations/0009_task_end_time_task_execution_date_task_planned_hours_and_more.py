"""Compatibility migration restored for the historical MGT migration graph.

The original project referenced this migration from 0010, but the file was
missing from the distributed ZIP.  The current model state does not contain
the historical Task fields named in this migration, so this node intentionally
contains no database operations.  Its purpose is to restore a consistent graph
without deleting data or rewriting already-applied migration history.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_landinglead"),
    ]

    operations = []
