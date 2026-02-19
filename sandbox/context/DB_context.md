# Intelligent Learning Platform – Database Context

## Overview

This database models an online learning platform where instructors create courses and students enroll, complete lessons, submit assignments, and receive certificates.

The system supports:
- Course publishing
- Student enrollments and progress tracking
- Assignments and grading
- Reviews and ratings
- Payments and transaction tracking
- Certification issuance

---

## User Roles

There are three types of users:

- **student** → Enrolls in courses, submits assignments, leaves reviews.
- **instructor** → Creates and manages courses.
- **admin** → Platform-level management.

---

## Courses

Each course:
- Belongs to exactly one instructor.
- Can belong to multiple categories.
- Contains multiple lessons.
- May contain multiple assignments.
- Can receive reviews from students.
- Can generate certificates upon completion.

Courses have:
- Difficulty level (beginner, intermediate, advanced)
- Publication status
- Price

---

## Enrollment Logic

- A student can enroll in multiple courses.
- A course can have multiple students.
- Enrollment tracks:
  - Progress percentage (0–100)
  - Completion timestamp
- A student cannot enroll twice in the same course.

---

## Lessons

Lessons:
- Belong to a course.
- Have a defined order (`position`).
- Include duration in minutes.

---

## Assignments & Submissions

Assignments:
- Belong to a course.
- Have a maximum score.
- May have a due date.

Submissions:
- One per student per assignment.
- Include score and instructor feedback.

---

## Reviews

- A student may leave one review per course.
- Rating is between 1 and 5.

---

## Payments

Payments track:
- Student
- Course
- Amount
- Payment method
- Status (pending, completed, failed, refunded)

---

## Certificates

Certificates are issued:
- Once per student per completed course.
- Only if course progress reaches 100%.

---

## Example Analytical Questions

The database supports queries such as:

- What are the top 5 highest-rated courses?
- Which instructor generates the most revenue?
- What is the completion rate per course?
- Which students have not submitted assignments before due date?
- What is the average grade per course?
- Monthly revenue breakdown.
- Most popular category by enrollment count.

---

## Business Rules

1. A student must be enrolled in a course to submit assignments.
2. A certificate is issued only if progress_pct = 100.
3. Each student can review a course only once.
4. Payments must be completed before access to paid courses.

---

This schema is designed to test:
- JOIN complexity
- Aggregations (SUM, AVG, COUNT)
- Subqueries
- CTEs
- Window functions
- Constraint reasoning
- Analytical SQL generation
