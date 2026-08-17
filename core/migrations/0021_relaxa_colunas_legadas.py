# O banco da homologação foi criado por ramos antigos de migrations e a
# core_userprofile tem uma coluna que NÃO existe no models.py atual:
# photo_content_type NOT NULL (herança do ramo que guardava a foto no
# próprio banco). O INSERT do cadastro público ignora a coluna-fantasma
# e estoura IntegrityError — foi o 500 do POST /primeiro-acesso/ pego
# no smoke test do RC28.
#
# Correção pontual: derrubar o NOT NULL dessa coluna, guardando pela
# existência (bancos recriados do zero — testes, SQLite — não a têm e
# nada acontece). Não destrói dado nenhum.

from django.db import migrations


def _relaxa_photo_content_type(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "postgresql":
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'core_userprofile'
              AND column_name = 'photo_content_type'
              AND is_nullable = 'NO'
            """
        )
        if cur.fetchone():
            cur.execute(
                'ALTER TABLE "core_userprofile" '
                'ALTER COLUMN "photo_content_type" DROP NOT NULL'
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_userprofile_role"),
    ]

    operations = [
        migrations.RunPython(_relaxa_photo_content_type, migrations.RunPython.noop),
    ]
