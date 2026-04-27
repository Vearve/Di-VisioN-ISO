# Product Scope And Priorities

## Scope Baseline (Current Release)

1. Multi-tenant OHS platform with role-based access and tenant isolation.
2. Operational safety modules: Incident, JSA, FRA, FLRA, Observation, PTO, CCV, Checklists, Toolbox Talks.
3. People and compliance modules: Employees, Contractors, Certifications, Training, Documents, Objectives.
4. Reliability modules: Schedules, reminders, CAPA, medical tracking, audit logs.
5. Analytics modules: KPI snapshots, warehouse facts, dashboard filtering by site/date.

## Priority Order

1. Tenant security and data isolation.
2. Core operational record reliability.
3. CAPA and medical risk controls.
4. Scheduling and reminder automation.
5. Analytics and decision support.
6. UX and navigation consistency.

## Definition Of Done (Per Module)

1. Model and migration applied.
2. Tenant + site linkage enforced.
3. CRUD UI reachable from navigation.
4. Role-based access checks enforced.
5. Audit log captured on create/update/delete where applicable.
6. Django checks clean and no pending migrations.

## Release Readiness Checklist

1. Run `manage.py makemigrations --check --dry-run`.
2. Run `manage.py migrate`.
3. Run `manage.py check`.
4. Run `manage.py capture_kpi_snapshots`.
5. Run `manage.py build_analytics_warehouse`.

## Next Minor Improvements

1. Add changed-field diffs in audit payloads.
2. Add automated tests for role permissions per module.
3. Add index tuning for large tenant analytics queries.
