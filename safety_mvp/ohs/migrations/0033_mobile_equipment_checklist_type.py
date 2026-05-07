from django.db import migrations, models


def migrate_lv_vehicle_to_mobile_equipment(apps, schema_editor):
    SafetyChecklist = apps.get_model("ohs", "SafetyChecklist")
    SafetyChecklist.objects.filter(checklist_type="LV Vehicle").update(
        checklist_type="Mobile Equipment"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ohs", "0032_siteprojectattachment"),
    ]

    operations = [
        migrations.RunPython(
            migrate_lv_vehicle_to_mobile_equipment,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="safetychecklist",
            name="checklist_type",
            field=models.CharField(
                choices=[
                    ("Daily", "Daily"),
                    ("Weekly", "Weekly"),
                    ("Monthly", "Monthly"),
                    ("Mobile Equipment", "Mobile Equipment Checklist"),
                    ("Lighting Tower", "Lighting Tower Inspection Checklist"),
                    ("Drilling Machine Surface", "Drilling Machine Surface Checklist"),
                    ("Environmental", "Environmental Checklist"),
                    ("Generator", "Generator Checklist"),
                    ("Other Operational", "Other Operational Checklist"),
                ],
                max_length=40,
            ),
        ),
    ]
