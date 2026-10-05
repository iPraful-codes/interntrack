CREATE TABLE IF NOT EXISTS applications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company    TEXT NOT NULL,
    role       TEXT NOT NULL,
    location   TEXT,
    status     TEXT NOT NULL DEFAULT 'Applied'
               CHECK (status IN ('Wishlist', 'Applied', 'Interview', 'Offer', 'Rejected')),
    applied_on TEXT NOT NULL DEFAULT (date('now')),
    link       TEXT,
    notes      TEXT
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status);
