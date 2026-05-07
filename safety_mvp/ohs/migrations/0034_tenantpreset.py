from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ohs', '0033_mobile_equipment_checklist_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantPreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ccv_target', models.PositiveIntegerField(default=20)),
                ('pto_target', models.PositiveIntegerField(default=20)),
                ('flra_target', models.PositiveIntegerField(default=500)),
                ('employee_target', models.PositiveIntegerField(default=0)),
                ('objective_target', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='presets', to='ohs.tenant')),
            ],
        ),
    ]
