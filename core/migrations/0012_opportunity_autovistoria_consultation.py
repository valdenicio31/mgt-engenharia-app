from django.db import migrations, models


def add_missing_opportunity_columns(apps, schema_editor):
    """Add only columns that are not already present in core_opportunity.

    Some deployed databases already contain the ``source`` column from an
    earlier/manual update, while Django's migration history does not know
    about it. A regular AddField therefore fails with DuplicateColumn.
    """
    Opportunity = apps.get_model("core", "Opportunity")
    table_name = Opportunity._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )
    existing_columns = {column.name for column in description}

    fields = [
        ("source", models.CharField(blank=True, max_length=60, verbose_name="origem")),
        (
            "communication_number",
            models.CharField(
                blank=True, max_length=50, verbose_name="número do comunicado"
            ),
        ),
        (
            "consultation_status",
            models.CharField(
                blank=True, max_length=180, verbose_name="situação consultada"
            ),
        ),
        (
            "consultation_notes",
            models.TextField(blank=True, verbose_name="observações da consulta"),
        ),
        (
            "consultation_address",
            models.CharField(
                blank=True, max_length=300, verbose_name="endereço consultado"
            ),
        ),
        (
            "source_url",
            models.URLField(
                blank=True, max_length=500, verbose_name="link da consulta"
            ),
        ),
        (
            "consulted_at",
            models.DateTimeField(
                blank=True, null=True, verbose_name="consultado em"
            ),
        ),
    ]

    for field_name, field in fields:
        if field_name in existing_columns:
            continue
        field.set_attributes_from_name(field_name)
        field.model = Opportunity
        schema_editor.add_field(Opportunity, field)
        existing_columns.add(field_name)


def noop_reverse(apps, schema_editor):
    # Intentionally preserve data/columns during rollback. This migration was
    # designed to reconcile databases with different pre-existing schemas.
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0011_client_photo")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_missing_opportunity_columns,
                    reverse_code=noop_reverse,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="opportunity",
                    name="source",
                    field=models.CharField(
                        blank=True, max_length=60, verbose_name="origem"
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="communication_number",
                    field=models.CharField(
                        blank=True,
                        max_length=50,
                        verbose_name="número do comunicado",
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="consultation_status",
                    field=models.CharField(
                        blank=True,
                        max_length=180,
                        verbose_name="situação consultada",
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="consultation_notes",
                    field=models.TextField(
                        blank=True, verbose_name="observações da consulta"
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="consultation_address",
                    field=models.CharField(
                        blank=True,
                        max_length=300,
                        verbose_name="endereço consultado",
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="source_url",
                    field=models.URLField(
                        blank=True,
                        max_length=500,
                        verbose_name="link da consulta",
                    ),
                ),
                migrations.AddField(
                    model_name="opportunity",
                    name="consulted_at",
                    field=models.DateTimeField(
                        blank=True, null=True, verbose_name="consultado em"
                    ),
                ),
            ],
        )
    ]
