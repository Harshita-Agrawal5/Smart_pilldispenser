from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Profile, Medicine, MedicineHistory, DispenserSlot, PillEvent


# ----------------- SAFE PROFILE GET -----------------
def get_user_role(user):
    profile, created = Profile.objects.get_or_create(user=user)
    return profile


# ----------------- DASHBOARD REDIRECT -----------------
def redirect_dashboard(user):
    profile = get_user_role(user)
    if profile.role == 'doctor':
        return redirect('doctor_dashboard')
    elif profile.role == 'patient':
        return redirect('user_dashboard')
    elif profile.role == 'caregiver':
        return redirect('caregiver_dashboard')
    else:
        return redirect('login')


def redirect_user(request):
    if request.user.is_authenticated:
        return redirect_dashboard(request.user)
    return redirect('login')


# ----------------- AUTH -----------------
def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_dashboard(user)
        else:
            return render(request, 'main/login.html', {'error': 'Invalid credentials'})
    return render(request, 'main/login.html')


def signup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        role = request.POST.get('role', '').lower()
        if not role:
            return render(request, 'main/signup.html', {'error': 'Please select a role'})
        if User.objects.filter(username=username).exists():
            return render(request, 'main/signup.html', {'error': 'User already exists'})
        user = User.objects.create_user(username=username, password=password)
        Profile.objects.create(user=user, role=role)
        return redirect('login')
    return render(request, 'main/signup.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    return redirect_dashboard(request.user)


# ----------------- DOCTOR DASHBOARD -----------------
@login_required
def doctor_dashboard(request):
    profile = get_user_role(request.user)
    if profile.role != 'doctor':
        return redirect('home')
    patients = User.objects.filter(profile__role='patient')
    return render(request, 'main/doctor_dashboard.html', {'patients': patients})


@login_required
def patient_detail(request, patient_id):
    profile = get_user_role(request.user)
    if profile.role != 'doctor':
        return redirect('home')
    patient       = get_object_or_404(User, id=patient_id, profile__role='patient')
    medicines     = Medicine.objects.filter(patient=patient).order_by('time')
    taken_count   = medicines.filter(status='taken').count()
    missed_count  = medicines.filter(status='missed').count()
    pending_count = medicines.count() - taken_count - missed_count

    # ✅ pass patient's profile so doctor can see prescription image
    patient_profile = patient.profile

    return render(request, 'main/patient_detail.html', {
        'patient':         patient,
        'patient_profile': patient_profile,
        'medicines':       medicines,
        'taken_count':     taken_count,
        'missed_count':    missed_count,
        'pending_count':   pending_count,
    })


# ----------------- UNIFIED ADD MEDICINE (Doctor / Patient / Caregiver) -----------------
@login_required
def add_medicine(request, patient_id=None):
    profile = get_user_role(request.user)
    role    = profile.role

    if role == 'doctor':
        if not patient_id:
            return redirect('doctor_dashboard')
        patient = get_object_or_404(User, id=patient_id, profile__role='patient')
    elif role == 'patient':
        patient = request.user
    elif role == 'caregiver':
        if not patient_id:
            return redirect('caregiver_dashboard')
        patient = get_object_or_404(User, id=patient_id, profile__role='patient')
    else:
        return redirect('home')

    if request.method == "POST":
        name   = request.POST.get('name',   '').strip()
        dosage = request.POST.get('dosage', '').strip()
        time   = request.POST.get('time',   '').strip()
        notes  = request.POST.get('notes',  '').strip()

        if not name or not dosage or not time:
            messages.error(request, "Please fill all required fields!")
            return redirect(request.path)

        med = Medicine.objects.create(
            patient       = patient,
            name          = name,
            dosage        = dosage,
            time          = time,
            notes         = notes,
            prescribed_by = request.user,
            status        = 'pending',
        )
        MedicineHistory.objects.create(medicine=med, action='pending')
        messages.success(request, f"Medicine '{name}' added successfully!")

        if role == 'doctor':
            return redirect('patient_detail', patient_id=patient.id)
        elif role == 'caregiver':
            return redirect('caregiver_dashboard')
        else:
            return redirect('user_dashboard')

    return render(request, 'main/add_medicine.html', {
        'patient': patient,
        'role':    role,
    })


# ----------------- PATIENT DASHBOARD -----------------
@login_required
def user_dashboard(request):
    profile = get_user_role(request.user)
    if profile.role != 'patient':
        return redirect('home')

    user      = request.user
    medicines = Medicine.objects.filter(patient=user).order_by('-id')

    print("DASHBOARD MEDICINES:", list(medicines.values('name', 'status')))

    taken_count   = medicines.filter(status='taken').count()
    missed_count  = medicines.filter(status='missed').count()
    pending_count = medicines.count() - taken_count - missed_count
    caregivers    = User.objects.filter(profile__role='caregiver')

    print("USER:", request.user.username)
    print("MEDICINES:", list(Medicine.objects.filter(patient=request.user).values('name', 'status')))

    if request.method == 'POST' and 'caregiver' in request.POST:
        caregiver_id = request.POST.get('caregiver')
        if caregiver_id:
            caregiver_user = User.objects.get(id=caregiver_id)
            profile.caregiver = caregiver_user
            profile.save()
            return redirect('user_dashboard')

    profile.refresh_from_db()

    from collections import defaultdict
    from django.utils import timezone

    grouped_medicines = defaultdict(list)
    for med in medicines:
        date = med.created_at.date() if hasattr(med, 'created_at') else timezone.now().date()
        grouped_medicines[date].append(med)
    grouped_medicines = dict(sorted(grouped_medicines.items(), reverse=True))

    today     = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)

    return render(request, 'main/user_dashboard.html', {
        'medicines':         medicines,
        'taken_count':       taken_count,
        'missed_count':      missed_count,
        'pending_count':     pending_count,
        'profile':           profile,
        'caregivers':        caregivers,
        'grouped_medicines': grouped_medicines,
        'today':             today,
        'yesterday':         yesterday,
    })


# ----------------- CAREGIVER DASHBOARD -----------------
@login_required
def caregiver_dashboard(request):
    profile = get_user_role(request.user)
    if profile.role != 'caregiver':
        return redirect('home')

    patients  = User.objects.filter(profile__caregiver=request.user)
    medicines = Medicine.objects.filter(patient__in=patients).order_by('time')

    taken_count   = medicines.filter(status='taken').count()
    missed_count  = medicines.filter(status='missed').count()
    pending_count = medicines.count() - taken_count - missed_count

    return render(request, 'main/caregiver_dashboard.html', {
        'patients':      patients,
        'medicines':     medicines,
        'taken_count':   taken_count,
        'missed_count':  missed_count,
        'pending_count': pending_count,
    })


# ----------------- MEDICINE HISTORY -----------------
@login_required
def medicine_history(request, patient_id=None):
    profile = get_user_role(request.user)
    role    = profile.role

    if role == 'doctor':
        medicines = Medicine.objects.filter(prescribed_by=request.user)
        if patient_id:
            medicines = medicines.filter(patient__id=patient_id)
    elif role == 'patient':
        medicines = Medicine.objects.filter(patient=request.user)
    elif role == 'caregiver':
        medicines = Medicine.objects.filter(patient__profile__caregiver=request.user)
    else:
        return redirect('home')

    history = MedicineHistory.objects.filter(medicine__in=medicines).order_by('-timestamp')
    return render(request, 'main/medicine_history.html', {'history': history, 'role': role})


# ----------------- DISPENSER -----------------
@login_required
def dispenser_status(request):
    profile = get_user_role(request.user)
    role    = profile.role
    if role not in ['patient', 'caregiver']:
        return redirect('home')
    if role == 'patient':
        slots = DispenserSlot.objects.filter(patient=request.user)
    else:
        slots = DispenserSlot.objects.filter(patient__profile__caregiver=request.user)
    return render(request, 'main/dispenser_status.html', {'slots': slots})


# =================================================================
# ✅ PRESCRIPTION IMAGE — upload / delete
# ONE image per patient. Visible to patient, caregiver, doctor.
# Upload page is separate — not part of add medicine form.
# =================================================================
@login_required
def upload_prescription(request, patient_id=None):
    """
    Any role can upload/replace the prescription image for a patient.
    Patient uploads for themselves.
    Doctor/Caregiver pass patient_id.
    """
    profile = get_user_role(request.user)
    role    = profile.role

    if role == 'patient':
        patient = request.user
    elif role in ('doctor', 'caregiver'):
        if not patient_id:
            return redirect('home')
        patient = get_object_or_404(User, id=patient_id, profile__role='patient')
    else:
        return redirect('home')

    patient_profile = patient.profile

    if request.method == 'POST':
        image = request.FILES.get('prescription_image')
        if image:
            # replace old image
            patient_profile.prescription_image = image
            patient_profile.save()
            messages.success(request, "Prescription image uploaded successfully!")
        else:
            messages.error(request, "Please select an image to upload.")
        # redirect back to where they came from
        if role == 'doctor':
            return redirect('patient_detail', patient_id=patient.id)
        elif role == 'caregiver':
            return redirect('caregiver_dashboard')
        else:
            return redirect('user_dashboard')

    return render(request, 'main/upload_prescription.html', {
        'patient':         patient,
        'patient_profile': patient_profile,
        'role':            role,
    })


@login_required
def delete_prescription(request, patient_id=None):
    """Delete the prescription image for a patient."""
    profile = get_user_role(request.user)
    role    = profile.role

    if role == 'patient':
        patient = request.user
    elif role in ('doctor', 'caregiver'):
        if not patient_id:
            return redirect('home')
        patient = get_object_or_404(User, id=patient_id, profile__role='patient')
    else:
        return redirect('home')

    patient_profile = patient.profile
    patient_profile.prescription_image = None
    patient_profile.save()
    messages.success(request, "Prescription image removed.")

    if role == 'doctor':
        return redirect('patient_detail', patient_id=patient.id)
    elif role == 'caregiver':
        return redirect('caregiver_dashboard')
    else:
        return redirect('user_dashboard')


# ----------------- API (POSTMAN INTEGRATION) -----------------
@api_view(['POST'])
def pill_event(request):
    event         = request.data.get("event")
    patient_name  = request.data.get("patient_name")
    medicine_name = request.data.get("medicine_name")

    if not (event and patient_name and medicine_name):
        return Response({"error": "Missing data"})

    patient = User.objects.filter(username__iexact=patient_name.strip()).first()
    if not patient:
        return Response({"error": "Patient not found"})

    from datetime import datetime
    med = Medicine.objects.create(
        patient=patient,
        name=medicine_name.strip(),
        time=datetime.now().time(),
        status="taken" if event == "pill_taken" else "missed"
    )
    MedicineHistory.objects.create(medicine=med, action=event)

    slot = DispenserSlot.objects.filter(
        patient=patient,
        medicine_name__iexact=medicine_name.strip()
    ).first()
    if slot:
        if slot.quantity > 0:
            slot.quantity -= 1
            slot.save()
    return Response({"message": "New entry created", "medicine": med.name, "status": med.status})


# ----------------- DASHBOARD (EVENT VIEW) -----------------
def dashboard(request):
    events = PillEvent.objects.order_by('-timestamp')[:10]
    return render(request, "dashboard.html", {"events": events})


@login_required
def take_medicine(request, med_id):
    med = get_object_or_404(Medicine, id=med_id, patient=request.user)
    med.status = 'taken'
    med.save()
    MedicineHistory.objects.create(medicine=med, action='taken')
    return redirect('user_dashboard')


@login_required
def mark_missed(request, med_id):
    med = get_object_or_404(Medicine, id=med_id, patient=request.user)
    med.status = 'missed'
    med.save()
    MedicineHistory.objects.create(medicine=med, action='missed')
    return redirect('user_dashboard')


# =================================================================
# API 1 — PATIENT STATUS
# =================================================================
@api_view(['GET'])
def patient_status(request):
    patient_name = request.query_params.get("name")
    if not patient_name:
        return Response({"error": "Please provide ?name=patient_username"})
    patient = User.objects.filter(username__iexact=patient_name.strip()).first()
    if not patient:
        return Response({"error": "Patient not found"})
    from django.utils import timezone
    today      = timezone.now().date()
    medicines  = Medicine.objects.filter(patient=patient, date=today)
    total      = medicines.count()
    taken      = medicines.filter(status='taken').count()
    missed     = medicines.filter(status='missed').count()
    pending    = medicines.filter(status='pending').count()
    compliance = f"{int((taken / total) * 100)}%" if total > 0 else "No medicines today"
    medicine_list = [
        {"name": m.name, "dosage": m.dosage or "N/A", "time": str(m.time), "status": m.status}
        for m in medicines
    ]
    return Response({
        "patient": patient.username, "date": str(today),
        "total_medicines": total, "taken": taken, "missed": missed,
        "pending": pending, "compliance": compliance, "today_medicines": medicine_list,
    })


# =================================================================
# API 2 — LOW STOCK ALERT
# =================================================================
@api_view(['POST'])
def low_stock_alert(request):
    patient_name       = request.data.get("patient_name")
    medicine_name      = request.data.get("medicine_name")
    quantity_remaining = request.data.get("quantity_remaining")
    if not (patient_name and medicine_name and quantity_remaining is not None):
        return Response({"error": "Missing data."})
    patient = User.objects.filter(username__iexact=patient_name.strip()).first()
    if not patient:
        return Response({"error": "Patient not found"})
    slot, _ = DispenserSlot.objects.get_or_create(
        patient=patient,
        medicine_name__iexact=medicine_name.strip(),
        defaults={'medicine_name': medicine_name.strip(), 'expected_medicine': medicine_name.strip(), 'quantity': quantity_remaining}
    )
    slot.quantity = int(quantity_remaining)
    slot.save()
    if slot.quantity == 0:
        alert_level, message = "CRITICAL", f"⛔ {medicine_name} is EMPTY! Refill immediately."
    elif slot.quantity <= 3:
        alert_level, message = "WARNING", f"⚠️ Only {slot.quantity} pills left. Refill soon."
    else:
        alert_level, message = "OK", f"✅ Stock OK. {slot.quantity} pills remaining."
    return Response({"patient": patient.username, "medicine": medicine_name,
                     "quantity_remaining": slot.quantity, "alert_level": alert_level, "message": message})


# =================================================================
# API 3 — WRONG MEDICINE
# =================================================================
@api_view(['POST'])
def wrong_medicine(request):
    patient_name = request.data.get("patient_name")
    expected     = request.data.get("expected")
    actual       = request.data.get("actual")
    if not (patient_name and expected and actual):
        return Response({"error": "Missing data."})
    patient = User.objects.filter(username__iexact=patient_name.strip()).first()
    if not patient:
        return Response({"error": "Patient not found"})
    slot = DispenserSlot.objects.filter(patient=patient, medicine_name__iexact=expected.strip()).first()
    if not slot:
        slot = DispenserSlot.objects.create(
            patient=patient, medicine_name=expected.strip(),
            expected_medicine=expected.strip(), actual_medicine=actual.strip(), quantity=0)
        return Response({"alert": "❌ WRONG MEDICINE DETECTED (new slot created)"})
    slot.actual_medicine = actual.strip()
    slot.save()
    alert   = "❌ WRONG MEDICINE" if slot.actual_medicine.lower() != slot.expected_medicine.lower() else "✅ Correct"
    message = f"Expected '{expected}' but got '{actual}'." if "❌" in alert else f"Medicine matches."
    return Response({"patient": patient.username, "expected": slot.expected_medicine,
                     "actual": slot.actual_medicine, "alert": alert, "message": message})


# ----------------- PROFILE VIEW -----------------
@login_required
def patient_profile_view(request, user_id):
    user            = get_object_or_404(User, id=user_id)
    profile         = user.profile
    medicines       = Medicine.objects.filter(patient=user).order_by('-id')
    return render(request, 'main/patient_profile.html', {
        'profile_user': user,
        'profile':      profile,
        'medicines':    medicines,
    })


# ----------------- EDIT PROFILE -----------------
@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        profile.age             = request.POST.get('age')
        profile.gender          = request.POST.get('gender')
        profile.phone           = request.POST.get('phone')
        profile.address         = request.POST.get('address')
        profile.medical_history = request.POST.get('medical_history')
        profile.save()
        return redirect('user_dashboard')
    return render(request, 'main/edit_profile.html', {'profile': profile})