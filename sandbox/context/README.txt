Place your database schema, documentation, or other context files in this directory.
The sandbox application will automatically read all text-based files in this folder (.txt, .sql, .md, .csv, .json) and add them to the System Prompt.

Example:
Create a file named `schema.sql` with your table definitions:

```sql
-- ============================================================
-- Intelligent Learning Platform - Relational Database Schema
-- ============================================================

-- ============================
-- USERS
-- ============================
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('student', 'instructor', 'admin')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);


-- ============================
-- COURSES
-- ============================
CREATE TABLE courses (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    instructor_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    price           NUMERIC(10,2) DEFAULT 0.00,
    level           VARCHAR(20) CHECK (level IN ('beginner', 'intermediate', 'advanced')),
    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_courses_instructor ON courses(instructor_id);
CREATE INDEX idx_courses_level ON courses(level);


-- ============================
-- CATEGORIES
-- ============================
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE course_categories (
    course_id   INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, category_id)
);


-- ============================
-- ENROLLMENTS
-- ============================
CREATE TABLE enrollments (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress_pct    NUMERIC(5,2) DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    completed_at    TIMESTAMP,
    UNIQUE(student_id, course_id)
);

CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);


-- ============================
-- LESSONS
-- ============================
CREATE TABLE lessons (
    id              SERIAL PRIMARY KEY,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    content         TEXT,
    duration_min    INTEGER CHECK (duration_min > 0),
    position        INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lessons_course ON lessons(course_id);


-- ============================
-- ASSIGNMENTS
-- ============================
CREATE TABLE assignments (
    id              SERIAL PRIMARY KEY,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    due_date        TIMESTAMP,
    max_score       INTEGER CHECK (max_score > 0),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assignments_course ON assignments(course_id);


-- ============================
-- SUBMISSIONS
-- ============================
CREATE TABLE submissions (
    id              SERIAL PRIMARY KEY,
    assignment_id   INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score           INTEGER,
    feedback        TEXT,
    UNIQUE(assignment_id, student_id)
);

CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX idx_submissions_student ON submissions(student_id);


-- ============================
-- REVIEWS
-- ============================
CREATE TABLE reviews (
    id              SERIAL PRIMARY KEY,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, student_id)
);

CREATE INDEX idx_reviews_course ON reviews(course_id);


-- ============================
-- PAYMENTS
-- ============================
CREATE TABLE payments (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    amount          NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    payment_method  VARCHAR(50) CHECK (payment_method IN ('credit_card', 'paypal', 'bank_transfer')),
    status          VARCHAR(20) CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    paid_at         TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payments_student ON payments(student_id);
CREATE INDEX idx_payments_course ON payments(course_id);


-- ============================
-- CERTIFICATES
-- ============================
CREATE TABLE certificates (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    issued_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    certificate_url TEXT,
    UNIQUE(student_id, course_id)
);

CREATE INDEX idx_certificates_student ON certificates(student_id);

```

The model will then know about this table.
