from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Base, User, HCP, Product, Sample, Interaction
import datetime
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./crm.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Seeding database
    db = SessionLocal()
    try:
        # Check if User exists, if not seed
        if db.query(User).count() == 0:
            rep = User(
                name="Sarah Rep",
                email="sarah.rep@example.com",
                territory_id="TERR-01",
                role="rep"
            )
            db.add(rep)
            db.commit()
            print("Seeded User.")

        # Check if HCP exists, if not seed
        if db.query(HCP).count() == 0:
            hcps = [
                HCP(
                    name="Dr. Amit Mehta",
                    specialty="Cardiology",
                    institution="Apollo Hospital",
                    npi_id="1982736450",
                    segment="KOL",
                    preferred_channel="visit"
                ),
                HCP(
                    name="Dr. Priya Sharma",
                    specialty="Pediatrics",
                    institution="Fortis Healthcare",
                    npi_id="1029384756",
                    segment="High",
                    preferred_channel="virtual"
                ),
                HCP(
                    name="Dr. Vikas Verma",
                    specialty="Oncology",
                    institution="Max Healthcare",
                    npi_id="1726354890",
                    segment="Medium",
                    preferred_channel="email"
                )
            ]
            for h in hcps:
                db.add(h)
            db.commit()
            print("Seeded HCPs.")

        # Check if Product exists, if not seed
        if db.query(Product).count() == 0:
            p_cardiox = Product(
                name="CardioX",
                indication="Hypertension",
                dosage_forms=["5mg", "10mg"]
            )
            p_pedrasafe = Product(
                name="PedraSafe",
                indication="Pediatric Fever",
                dosage_forms=["50ml"]
            )
            p_oncoshield = Product(
                name="OncoShield",
                indication="Oncology",
                dosage_forms=["100mg"]
            )
            db.add(p_cardiox)
            db.add(p_pedrasafe)
            db.add(p_oncoshield)
            db.commit()
            print("Seeded Products.")

        # Check if Sample exists, if not seed
        if db.query(Sample).count() == 0:
            # Look up seeded product IDs
            p_cardiox = db.query(Product).filter(Product.name == "CardioX").first()
            p_pedrasafe = db.query(Product).filter(Product.name == "PedraSafe").first()
            p_oncoshield = db.query(Product).filter(Product.name == "OncoShield").first()
            
            samples = [
                Sample(
                    product_id=p_cardiox.id,
                    lot_number="CX10-2027",
                    expiry_date=datetime.date(2027, 12, 31)
                ),
                Sample(
                    product_id=p_cardiox.id,
                    lot_number="CX10-EXP",
                    expiry_date=datetime.date(2025, 6, 1)  # Expired
                ),
                Sample(
                    product_id=p_pedrasafe.id,
                    lot_number="PS50-2027",
                    expiry_date=datetime.date(2027, 8, 31)
                ),
                Sample(
                    product_id=p_oncoshield.id,
                    lot_number="OS100-2027",
                    expiry_date=datetime.date(2027, 10, 31)
                )
            ]
            for s in samples:
                db.add(s)
            db.commit()
            print("Seeded Samples.")
            
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()
