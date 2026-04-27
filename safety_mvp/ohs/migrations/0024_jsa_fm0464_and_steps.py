import datetime

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def copy_task_to_job_task(apps, schema_editor):
	JSA = apps.get_model('ohs', 'JSA')
	for jsa in JSA.objects.all():
		if not jsa.job_task:
			jsa.job_task = jsa.task
			jsa.save(update_fields=['job_task'])


class Migration(migrations.Migration):

	dependencies = [
		('ohs', '0023_alter_ccvcriticalcontrolverification_ccv_type'),
	]

	operations = [
		migrations.AddField(
			model_name='jsa',
			name='document_reference',
			field=models.CharField(default='FM0464', max_length=50),
		),
		migrations.AlterField(
			model_name='jsa',
			name='revision_number',
			field=models.CharField(default='09', max_length=50),
		),
		migrations.AlterField(
			model_name='jsa',
			name='task',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.AlterField(
			model_name='jsa',
			name='hazards',
			field=models.TextField(blank=True),
		),
		migrations.AlterField(
			model_name='jsa',
			name='controls',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='total_pages',
			field=models.CharField(blank=True, max_length=20),
		),
		migrations.AddField(
			model_name='jsa',
			name='date_of_issue',
			field=models.DateField(default=datetime.date(2024, 5, 15)),
		),
		migrations.AddField(
			model_name='jsa',
			name='date_of_next_review',
			field=models.DateField(default=datetime.date(2026, 5, 14)),
		),
		migrations.AddField(
			model_name='jsa',
			name='jsa_number',
			field=models.CharField(blank=True, max_length=100),
		),
		migrations.AddField(
			model_name='jsa',
			name='work_order_number',
			field=models.CharField(blank=True, max_length=100),
		),
		migrations.AddField(
			model_name='jsa',
			name='job_task',
			field=models.CharField(default='', max_length=500),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='jsa',
			name='plant_area',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.AddField(
			model_name='jsa',
			name='assessment_date',
			field=models.DateField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='senior_supervisor_name',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.AddField(
			model_name='jsa',
			name='senior_supervisor_signature',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='work_group_supervisor_name',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.AddField(
			model_name='jsa',
			name='work_group_supervisor_signature',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='permit_to_work',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='excavation_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hot_work_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hv_electrical_isolation_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hv_vicinity_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='radiation_work_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='working_at_height_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='chemical_pump_pipe_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='confined_space_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='other_permit',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='other_permit_description',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.RenameField(
			model_name='jsa',
			old_name='required_ppe',
			new_name='additional_ppe_requirements',
		),
		migrations.RenameField(
			model_name='jsa',
			old_name='tools_equipment_used',
			new_name='special_tools_equipment',
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_competent_capable_controlled',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_identify_control_hazards',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_safe_lifting_operations',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_drive_safely',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_energy_isolation',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_confined_space_entry',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_work_at_heights',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_surface_underground',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_equipment_safeguards',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='fpc_chemicals_hazardous_substances',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazardous_materials',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='fire_emergency_equipment',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='supports_lift_plan',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='supports_sds',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='supports_emergency_action_plan',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='safe_work_procedure_possible',
			field=models.BooleanField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_flora_fauna',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_electrical',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_mechanical',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_chemical',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_dust_fume',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_soil_erosion',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_stored_energy',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_live_equipment',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_manual_handling',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_radiation',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_spills_water',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_falling_equipment',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_noise',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_ignition_sources',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_spills_ground',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_fire_explosives',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_light_dark',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_rock_falls',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='hazard_concealed_services',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_rain',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_thunder',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_lightning',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_extreme_temperatures',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_other',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='jsa',
			name='weather_other_description',
			field=models.CharField(blank=True, max_length=255),
		),
		migrations.AddField(
			model_name='jsa',
			name='team_member_acknowledgements',
			field=models.JSONField(blank=True, default=list),
		),
		migrations.AddField(
			model_name='jsa',
			name='senior_supervisor_acknowledgement',
			field=models.TextField(blank=True),
		),
		migrations.AddField(
			model_name='jsa',
			name='daily_review_log',
			field=models.JSONField(blank=True, default=list),
		),
		migrations.AddField(
			model_name='jsa',
			name='created_at',
			field=models.DateTimeField(default=timezone.now, editable=False),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='jsa',
			name='updated_at',
			field=models.DateTimeField(default=timezone.now),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='jsa',
			name='created_at',
			field=models.DateTimeField(auto_now_add=True),
		),
		migrations.AlterField(
			model_name='jsa',
			name='updated_at',
			field=models.DateTimeField(auto_now=True),
		),
		migrations.RemoveField(
			model_name='jsa',
			name='required_permit',
		),
		migrations.RemoveField(
			model_name='jsa',
			name='trigger_for_review',
		),
		migrations.CreateModel(
			name='JSAStep',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('step_number', models.PositiveIntegerField()),
				('job_step', models.TextField()),
				('job_step_hazard', models.TextField()),
				('current_controls', models.TextField()),
				('evaluation_control_type', models.CharField(blank=True, choices=[('elimination', 'Elimination'), ('substitution', 'Substitution'), ('engineering', 'Engineering'), ('administrative', 'Administrative'), ('ppe', 'PPE')], max_length=20)),
				('likelihood_before', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('consequence_before', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('residual_risk_before', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('required_additional_actions', models.TextField(blank=True)),
				('likelihood_after', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('consequence_after', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('residual_risk_after', models.CharField(blank=True, choices=[('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'), ('4', 'High'), ('5', 'Very High')], max_length=20)),
				('jsa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='ohs.jsa')),
			],
			options={
				'ordering': ('jsa', 'step_number'),
				'unique_together': {('jsa', 'step_number')},
			},
		),
		migrations.RunPython(copy_task_to_job_task, migrations.RunPython.noop),
	]
