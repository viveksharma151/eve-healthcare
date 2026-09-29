"""
Database seeding script.
Populates initial diagnostic tests, diagnostic centres with pricing, and sample accounts.
Usage: python seed.py
"""
import sys
from decimal import Decimal
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest, CentreTest
from app.core.security import get_password_hash


def seed_data():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(DiagnosticCentre).first():
            print("Database already contains data. Skipping seeding.")
            return

        print("Seeding users...")
        test_patient = User(
            email="patient@example.com",
            full_name="Aarav Sharma",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_staff=False,
        )
        admin_user = User(
            email="admin@evehealthcare.com",
            full_name="Staff Admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_staff=True,
        )
        db.add_all([test_patient, admin_user])
        db.flush()

        print("Seeding diagnostic tests...")
        test_cbc = DiagnosticTest(
            code="CBC",
            name="Complete Blood Count",
            description="Evaluates red cells, white cells, and platelets to detect anemia and infections.",
        )
        test_lipid = DiagnosticTest(
            code="LIPID",
            name="Lipid Profile",
            description="Measures cholesterol levels including HDL, LDL, and triglycerides.",
        )
        test_thyroid = DiagnosticTest(
            code="THYROID",
            name="Thyroid Stimulating Hormone (TSH)",
            description="Screens for thyroid gland dysfunction and metabolic health.",
        )
        test_lft = DiagnosticTest(
            code="LFT",
            name="Liver Function Test",
            description="Comprehensive panel measuring enzymes, proteins, and bilirubin.",
        )
        test_kft = DiagnosticTest(
            code="KFT",
            name="Kidney Function Test (Renal Profile)",
            description="Assesses kidney health via urea, creatinine, and electrolytes.",
        )

        db.add_all([test_cbc, test_lipid, test_thyroid, test_lft, test_kft])
        db.flush()

        print("Seeding diagnostic centres...")
        centre_bangalore = DiagnosticCentre(
            name="CareMax Diagnostic Centre - Indiranagar",
            location="100 Feet Rd, Indiranagar, Bengaluru, Karnataka",
            contact_phone="+91 80 4123 4567",
            is_active=True,
        )
        centre_mumbai = DiagnosticCentre(
            name="Apollo Diagnostics - Bandra West",
            location="Hill Road, Bandra West, Mumbai, Maharashtra",
            contact_phone="+91 22 6789 0123",
            is_active=True,
        )
        centre_delhi = DiagnosticCentre(
            name="Metro Health Diagnostics - Connaught Place",
            location="Barakhamba Road, Connaught Place, New Delhi",
            contact_phone="+91 11 2345 6789",
            is_active=True,
        )

        db.add_all([centre_bangalore, centre_mumbai, centre_delhi])
        db.flush()

        print("Mapping tests to centres with centre-specific pricing...")
        centre_tests = [
            # CareMax Bangalore
            CentreTest(centre_id=centre_bangalore.id, test_id=test_cbc.id, price=Decimal("350.00")),
            CentreTest(centre_id=centre_bangalore.id, test_id=test_lipid.id, price=Decimal("750.00")),
            CentreTest(centre_id=centre_bangalore.id, test_id=test_thyroid.id, price=Decimal("450.00")),
            CentreTest(centre_id=centre_bangalore.id, test_id=test_lft.id, price=Decimal("800.00")),

            # Apollo Mumbai
            CentreTest(centre_id=centre_mumbai.id, test_id=test_cbc.id, price=Decimal("400.00")),
            CentreTest(centre_id=centre_mumbai.id, test_id=test_lipid.id, price=Decimal("850.00")),
            CentreTest(centre_id=centre_mumbai.id, test_id=test_kft.id, price=Decimal("700.00")),

            # Metro Health Delhi
            CentreTest(centre_id=centre_delhi.id, test_id=test_cbc.id, price=Decimal("300.00")),
            CentreTest(centre_id=centre_delhi.id, test_id=test_thyroid.id, price=Decimal("400.00")),
            CentreTest(centre_id=centre_delhi.id, test_id=test_lft.id, price=Decimal("750.00")),
            CentreTest(centre_id=centre_delhi.id, test_id=test_kft.id, price=Decimal("650.00")),
        ]
        db.add_all(centre_tests)

        db.commit()
        print("Database seeded successfully!")
        print("\nDefault Accounts:")
        print("  Patient : patient@example.com / password123")
        print("  Admin   : admin@evehealthcare.com / admin123")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
