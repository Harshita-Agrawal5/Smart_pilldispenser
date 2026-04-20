# Smart Pill Dispenser System

IoT-based medication management platform with role-based dashboards 
for Doctors, Patients, and Caregivers.

## Tech Stack
- Python 3.10+
- Django 4.2
- Django REST Framework
- Bootstrap 5
- SQLite

## Setup Instructions

1. Clone the repo
   git clone https://github.com/yourusername/smart-pill-dispenser.git
   cd smart-pill-dispenser

2. Create virtual environment
   python -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (Mac/Linux)

3. Install dependencies
   pip install -r requirements.txt

4. Run migrations
   python manage.py makemigrations
   python manage.py migrate

5. Create superuser (optional)
   python manage.py createsuperuser

6. Run the server
   python manage.py runserver

7. Open browser
   http://127.0.0.1:8000

## API Endpoints (test via Postman)

POST /api/pill-event/
POST /api/low-stock/
POST /api/wrong-medicine/
GET  /api/patient-status/?name=username

## User Roles
- Doctor: manage patients, add medicines, view prescriptions
- Patient: view medicines, mark taken/missed, upload prescription
- Caregiver: monitor assigned patients, add medicines
