"""Fill the database with fictional demo data: python seed.py"""
import sqlite3
from datetime import date, timedelta

from app import create_app

ROWS = [
    ("Northwind Labs", "Junior Web Developer", "Remote", "Interview", 3, "https://example.com/jobs/1", "Technical call booked"),
    ("Brightloop", "Data Analyst Intern", "Milan, Italy", "Applied", 5, None, None),
    ("Kestrel Systems", "Graduate Software Engineer", "Berlin, Germany", "Applied", 9, None, "Referred by a friend"),
    ("Pixelforge", "Frontend Intern", "Remote", "Rejected", 12, None, "Asked for more React"),
    ("Tessera Data", "Junior Data Engineer", "Amsterdam, Netherlands", "Offer", 20, None, "Reply by Friday"),
    ("Lumen Works", "Backend Intern (Python)", "Remote", "Applied", 16, None, None),
    ("Orbit Health", "Junior Full-Stack Developer", "London, UK", "Wishlist", 1, "https://example.com/jobs/7", "Apply after finishing project"),
]


def main():
    app = create_app()
    db = sqlite3.connect(app.config["DATABASE"])
    if db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]:
        print("Database already has data, nothing seeded.")
        return
    today = date.today()
    db.executemany(
        "INSERT INTO applications (company, role, location, status, applied_on, link, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(c, r, l, s, (today - timedelta(days=d)).isoformat(), link, n) for c, r, l, s, d, link, n in ROWS],
    )
    db.commit()
    print(f"Seeded {len(ROWS)} applications.")


if __name__ == "__main__":
    main()
