from django.urls import path
from . import views

urlpatterns = [
    # Home / Auth
    path('', views.redirect_user, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # Doctor
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/patient/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('doctor/patient/<int:patient_id>/add_medicine/', views.add_medicine, name='add_medicine'),

    # Patient
    path('patient/', views.user_dashboard, name='user_dashboard'),
    path('take/<int:med_id>/', views.take_medicine, name='take_medicine'),
    path('missed/<int:med_id>/', views.mark_missed, name='mark_missed'),
    path('patient/add_medicine/', views.add_medicine, name='patient_add_medicine'),

    # Caregiver
    path('caregiver/', views.caregiver_dashboard, name='caregiver_dashboard'),
    path('caregiver/patient/<int:patient_id>/add_medicine/', views.add_medicine, name='caregiver_add_medicine'),

    # Medicine History
    path('history/', views.medicine_history, name='medicine_history'),
    path('history/<int:patient_id>/', views.medicine_history, name='medicine_history_patient'),

    # (duplicate kept as requested)
    path('doctor/patient/<int:patient_id>/', views.patient_detail, name='patient_detail'),

    path('dispenser/', views.dispenser_status, name='dispenser_status'),

    # ✅ PRESCRIPTION IMAGE — upload & delete (separate from add medicine)
    path('prescription/upload/', views.upload_prescription, name='upload_prescription'),
    path('prescription/upload/<int:patient_id>/', views.upload_prescription, name='upload_prescription_for'),
    path('prescription/delete/', views.delete_prescription, name='delete_prescription'),
    path('prescription/delete/<int:patient_id>/', views.delete_prescription, name='delete_prescription_for'),

    # APIs
    path('api/pill-event/', views.pill_event),
    path('dashboard/', views.dashboard),
    path('api/patient-status/', views.patient_status),
    path('api/low-stock/', views.low_stock_alert),
    path('api/wrong-medicine/', views.wrong_medicine),

    # Profile
    path('profile/<int:user_id>/', views.patient_profile_view, name='patient_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
]