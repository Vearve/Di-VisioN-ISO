# Tenant Data Scoping Security Audit - views.py

**File:** `safety_mvp/ohs/views.py`  
**Status:** GENERALLY SECURE with 2 minor issues identified  
**Overall Risk:** LOW (Most queries properly scoped, but best practices not always followed)

---

## Issues Found

### ⚠️ ISSUE #1: Form Save Without Commit=False (Low Risk)

**Location:** [Line 305](safety_mvp/ohs/views.py#L305) in `presets_page()`

**Code:**
```python
preset, _ = TenantPreset.objects.get_or_create(tenant=current_tenant)

if request.method == 'POST':
    form = TenantPresetForm(request.POST, instance=preset)
    if form.is_valid():
        form.save()  # ⚠️ No commit=False, no explicit tenant setting
```

**Risk:** LOW - Instance already has `tenant` set from `get_or_create()`, but relying on instance field preservation is not best practice.

**Recommendation:**
```python
if form.is_valid():
    instance = form.save(commit=False)
    instance.tenant = current_tenant
    instance.save()
```

---

### ⚠️ ISSUE #2: JSAStep Bulk Create Without Explicit Tenant

**Location:** [Lines 731-735](safety_mvp/ohs/views.py#L731-L735) in `save_jsa_steps()` callback

**Code:**
```python
jsa_instance.steps.all().delete()
if step_rows:
    JSAStep.objects.bulk_create([
        JSAStep(jsa=jsa_instance, **row) for row in step_rows
    ])
```

**Risk:** MEDIUM (if JSAStep model has separate `tenant` field)

**Issue:** JSAStep objects created without explicitly setting tenant field. If `JSAStep` model has:
- A separate `tenant` field (ForeignKey)
- A `tenant_id` that's NOT auto-populated from JSA relationship
- Middleware/signals that expect explicit tenant setting

Then this could create records without tenant association.

**Recommendation:**
```python
if step_rows:
    jsa_steps_to_create = []
    for row in step_rows:
        step = JSAStep(jsa=jsa_instance, **row)
        # Ensure tenant is set if JSAStep has separate tenant field
        if hasattr(step, 'tenant'):
            step.tenant = jsa_instance.tenant
        jsa_steps_to_create.append(step)
    JSAStep.objects.bulk_create(jsa_steps_to_create)
```

---

## ✅ Properly Scoped Queries (Secure)

### 1. _scope_queryset Helper Usage
**Lines:** 69-73, 105, 513, 534, 540, 550

All queries using the `_scope_queryset()` helper are properly scoped:
```python
_scope_queryset(Employee.objects.all(), current_tenant, current_site)
_scope_queryset(model.objects.all(), current_tenant, current_site)
```

### 2. Explicit Tenant Filtering in _module_page()
**Lines:** 513-551

The `_module_page()` function (used by most views) properly:
- ✅ Checks `if current_tenant is None: return empty queryset`
- ✅ Uses `_scope_queryset()` for all model queries
- ✅ Validates `form.is_valid()` before save
- ✅ Uses `form.save(commit=False)` pattern
- ✅ Explicitly sets tenant on instance before save
- ✅ Calls `form.save_m2m()` after instance.save()

**Code pattern (Lines 555-566):**
```python
form = form_class(request.POST, request.FILES, tenant=current_tenant, instance=edit_instance)
if form.is_valid() and current_tenant:
    instance = form.save(commit=False)
    instance.tenant = current_tenant
    if current_site and hasattr(instance, 'site_id'):
        instance.site = current_site
    for field in (auto_user_fields or []):
        if hasattr(instance, field):
            setattr(instance, field, request.user)
    instance.save()
    form.save_m2m()
```

### 3. SiteProjectAttachment Queries
**Lines:** 348-351, 384-389

All SiteProjectAttachment queries properly filter by tenant:
```python
attachment = SiteProjectAttachment.objects.filter(
    tenant=current_tenant,
    id=delete_attachment_id,
).first()

SiteProjectAttachment.objects.create(
    tenant=current_tenant,
    site_project=instance,
    file=uploaded_file,
    uploaded_by=request.user if request.user.is_authenticated else None,
)
```

### 4. Site Queryset Filtering
**Lines:** 336, 362, 363, 374, 441

All site queries use scoped querysets:
```python
site_qs = SiteProject.objects.none()
if current_tenant:
    site_qs = SiteProject.objects.filter(tenant=current_tenant).order_by('-id')

# Later filtered for specific records
edit_instance = site_qs.filter(id=edit_id).first()
deleted, _ = site_qs.filter(id=delete_id).delete()
```

### 5. Related Model Counts in site_cards Loop
**Lines:** 399-411

All related queries properly filter by tenant:
```python
'incidents_count': Incident.objects.filter(tenant=current_tenant, site=site).count(),
'jsa_count': JSA.objects.filter(tenant=current_tenant, site=site).count(),
'fra_count': FRA.objects.filter(tenant=current_tenant, site=site).count(),
'employees_count': Employee.objects.filter(tenant=current_tenant, site=site).count(),
'training_count': TrainingMatrix.objects.filter(tenant=current_tenant, site=site).count(),
'objectives_count': Objective.objects.filter(tenant=current_tenant, site=site).count(),
```

### 6. Center Pages Queries
**Lines:** 210-239**

All center pages (schedule_center, capa_center, medical_center, analytics_dashboard) properly:
- ✅ Check `if current_tenant is None: return empty queryset`
- ✅ Filter all queries by `tenant=current_tenant`
- ✅ Apply additional filters as needed

---

## Form Validation Checks

All form POST handling includes `is_valid()` checks:
- ✅ Line 305: `if form.is_valid():`
- ✅ Line 553: `if form.is_valid() and current_tenant:`
- ✅ Proper form handling in all module pages through `_module_page()` helper

---

## ✅ Data Exposure Risks - NOT FOUND

No evidence of:
- ❌ Unfiltered `.objects.all()` queries without _scope_queryset
- ❌ `.objects.filter()` calls missing tenant= parameter
- ❌ `.objects.get()` calls without tenant checking
- ❌ `.objects.first()` on unscoped querysets
- ❌ form.save() without validation in critical paths
- ❌ SiteProject.objects queries without tenant filter
- ❌ Employee.objects queries without tenant filter
- ❌ Missing tenant field on create operations

---

## Summary

| Category | Status | Count |
|----------|--------|-------|
| Queries Using _scope_queryset | ✅ Safe | 10+ |
| Explicit Tenant Filtering | ✅ Safe | 20+ |
| Form Validation Before Save | ✅ Safe | All |
| Potential Issues | ⚠️ Minor | 2 |
| Data Exposure Risks | ✅ None Found | 0 |

---

## Recommendations Priority

1. **Priority: HIGH** - Fix JSAStep.objects.bulk_create to ensure tenant is set (Line 733)
   - Verify if JSAStep has separate tenant field
   - Add explicit tenant assignment if needed

2. **Priority: MEDIUM** - Update presets_page form.save() to use commit=False pattern (Line 305)
   - Improves consistency with other forms
   - More explicit tenant handling
   - Better for future maintenance

3. **Priority: LOW** - Code is generally well-architected with good multi-tenant scoping
   - Consider documenting the _scope_queryset pattern for team
   - Consider linting rule to catch unscoped .objects.all() calls

---

## Related Files to Check

- `safety_mvp/ohs/models.py` - Check JSAStep model for tenant field definition
- `safety_mvp/ohs/forms.py` - Check if forms explicitly handle tenant in save()
- `safety_mvp/ohs/middleware.py` - Verify tenant_context middleware is properly setting request.current_tenant
