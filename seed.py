from app import app
from models import db, User, Note
from faker import Faker

fake = Faker()

with app.app_context():
    print("Clearing existing database...")
    Note.query.delete()
    User.query.delete()

    print("Seeding users and notes...")

    # Create dummy users
    users = []
    for _ in range(3):
        user = User(username=fake.user_name())
        user.password_hash = "password123"
        db.session.add(user)
        users.append(user)

    db.session.commit()

    # Create dummy notes for each user
    for user in users:
        for _ in range(5):
            note = Note(
                title=fake.sentence(nb_words=4),
                content=fake.paragraph(nb_sentences=3),
                user_id=user.id
            )
            db.session.add(note)

    db.session.commit()
    print("Database seeded successfully! 🌱")