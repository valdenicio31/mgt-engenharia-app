from django.db import migrations


def add_missing_opportunity_columns(apps, schema_editor):
    """Reconcile databases created from every historical MGT 1.0 branch.

    Migration 0012 had to support databases that already contained some
    columns. In a fresh test database, however, its historical model state did
    not expose the new fields reliably to every supported Django version.
    At this final graph node the fields are present in state, so we can safely
    add only the physical columns that are still missing.
    """
    Opportunity = apps.get_model("core", "Opportunity")
    table_name = Opportunity._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )
    existing_columns = {column.name for column in description}

    field_names = (
        "source",
        "communication_number",
        "consultation_status",
        "consultation_notes",
        "consultation_address",
        "source_url",
        "consulted_at",
    )
    for field_name in field_names:
        if field_name not in existing_columns:
            schema_editor.add_field(
                Opportunity, Opportunity._meta.get_field(field_name)
            )
            existing_columns.add(field_name)


def preserve_columns(apps, schema_editor):
    # This is a compatibility/reconciliation migration. Rolling it back must
    # not destroy columns or operational data.
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0016_merge_rc13_client_official_address")]

    operations = [
        migrations.RunPython(
            add_missing_opportunity_columns,
            reverse_code=preserve_columns,
        )
    ]
