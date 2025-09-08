from app.db.session import SessionLocal
from app.db.models import User
from passlib.context import CryptContext

email = "admin@example.com"
password = "admin"
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

with SessionLocal() as db:
    u = db.query(User).filter(User.email == email).one_or_none()
    if u:
        print("User already exists:", u.email)
    else:
        user = User(email=email, hashed_password=pwd.hash(password), role="admin")
        db.add(user)
        db.commit()
        print("Created admin:", user.id, user.email)

