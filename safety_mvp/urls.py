"""
URL configuration for safety_mvp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from safety_mvp.ohs import views  # Use your actual app name

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.safe_root, name='home'),
    path('dashboard/', views.safe_root, name='dashboard'),
    path('app/incidents/', views.incidents_page, name='incidents_page'),
    path('app/jsa/', views.jsa_page, name='jsa_page'),
    path('app/fra/', views.fra_page, name='fra_page'),
    path('app/flra/', views.flra_page, name='flra_page'),
    path('app/observations/', views.observations_page, name='observations_page'),
    path('app/pto-chemicals/', views.pto_chemicals_page, name='pto_chemicals_page'),
    path('app/ccv/', views.ccv_page, name='ccv_page'),
    path('app/checklists/', views.checklists_page, name='checklists_page'),
    path('app/toolbox-talks/', views.toolbox_talks_page, name='toolbox_talks_page'),
    path('app/employees/', views.employees_page, name='employees_page'),
    path('app/attendance/', views.attendance_page, name='attendance_page'),
    path('app/contractors/', views.contractors_page, name='contractors_page'),
    path('app/certifications/', views.certifications_page, name='certifications_page'),
    path('app/training/', views.training_page, name='training_page'),
    path('app/documents/', views.documents_page, name='documents_page'),
    path('app/materials/', views.materials_page, name='materials_page'),
    path('app/objectives/', views.objectives_page, name='objectives_page'),
    path('app/presets/', views.presets_page, name='presets_page'),
    path('app/schedules/', views.schedules_page, name='schedules_page'),
    path('app/capa/', views.capa_page, name='capa_page'),
    path('app/medical-profiles/', views.medical_profiles_page, name='medical_profiles_page'),
    path('app/medical-assessments/', views.medical_assessments_page, name='medical_assessments_page'),
    path('app/sites/', views.site_projects_page, name='site_projects_page'),
    path('app/sites/manage/<int:site_id>/', views.site_manage_page, name='site_manage_page'),
    path('app/sites/<int:site_id>/presets/', views.site_presets_page, name='site_presets_page'),
    path('app/monthly-health-reports/', views.monthly_site_health_reports_page, name='monthly_site_health_reports_page'),
    path('export/pdf/<str:module_name>/', views.export_to_pdf, name='export_pdf'),
    path('schedules/', views.schedule_center, name='schedule_center'),
    path('capa/', views.capa_center, name='capa_center'),
    path('medical/', views.medical_center, name='medical_center'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
]
