from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('guardian', '0027_scitoken_pipeline_ubermigration')
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE guardian_userobjectpermission
                ALTER COLUMN object_pk TYPE varchar(255) USING object_pk::varchar;
                
                ALTER TABLE guardian_groupobjectpermission
                ALTER COLUMN object_pk TYPE varchar(255) USING object_pk::varchar;
            """,
            reverse_sql="""
                ALTER TABLE guardian_userobjectpermission
                ALTER COLUMN object_pk TYPE integer USING object_pk::integer;
                
                ALTER TABLE guardian_groupobjectpermission
                ALTER COLUMN object_pk TYPE integer USING object_pk::integer;
            """
        ),
        migrations.AlterField(
            model_name='groupobjectpermission',
            name='object_pk',
            field=models.CharField(max_length=255, verbose_name='object ID'),
        ),
        migrations.AlterField(
            model_name='userobjectpermission',
            name='object_pk',
            field=models.CharField(max_length=255, verbose_name='object ID'),
        ),
    ]

