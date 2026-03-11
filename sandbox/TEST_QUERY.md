# Mid-Level Test Scenario

This query tests **JOINs, Aggregation, Filtering, Grouping, Ordering, and Limiting**.

## Natural Language Query
> "Who are the top 3 instructors generating the most revenue from 'advanced' courses?"

## Expected Behavior
1.  **Thinking Process**: The model should identify the need to join `users` (instructors), `courses` (for level), and `payments` (for revenue).
2.  **Clarification**: The model *might* ask about the time range (e.g., "all time?"). If so, answer "All time".
3.  **SQL Generation**: It should produce a single `SELECT` statement.

## Reference SQL (MySQL 8+)
```sql
SELECT 
    u.first_name, 
    u.last_name, 
    SUM(p.amount) AS total_revenue
FROM users u
JOIN courses c ON c.instructor_id = u.id
JOIN payments p ON p.course_id = c.id
WHERE c.level = 'advanced'
GROUP BY u.id, u.first_name, u.last_name
ORDER BY total_revenue DESC
LIMIT 3;
```

---

# Simple Test Scenario

This query tests **basic JOIN, Aggregation, and Ordering**.

## Natural Language Query
> "What are the top 5 highest-rated courses and who teaches them?"

## Expected Behavior
1.  **Thinking Process**: The model should join `courses` with `reviews` (for ratings) and `users` (for instructor name).
2.  **Clarification**: None expected — straightforward query.
3.  **SQL Generation**: A single `SELECT` with `AVG`, `GROUP BY`, and `ORDER BY`.

## Reference SQL (MySQL 8+)
```sql
SELECT
    c.title,
    u.first_name,
    u.last_name,
    AVG(r.rating) AS avg_rating,
    COUNT(r.id) AS review_count
FROM courses c
JOIN users u ON u.id = c.instructor_id
JOIN reviews r ON r.course_id = c.id
GROUP BY c.id, c.title, u.first_name, u.last_name
ORDER BY avg_rating DESC
LIMIT 5;
```

---

# Subquery Test Scenario

This query tests **Subqueries, Date Filtering, and Constraint Reasoning**.

## Natural Language Query
> "Which students have not submitted any assignment before its due date?"

## Expected Behavior
1.  **Thinking Process**: The model should identify students who have submissions but none of them were before the assignment's due date, or students with pending assignments past due.
2.  **Clarification**: The model *might* ask whether to include students with no submissions at all. If so, answer "Only students who have at least one assignment due."
3.  **SQL Generation**: Should use a subquery or `NOT EXISTS` / `LEFT JOIN ... IS NULL` pattern.

## Reference SQL (MySQL 8+)
```sql
SELECT DISTINCT
    u.id,
    u.first_name,
    u.last_name
FROM users u
JOIN enrollments e ON e.student_id = u.id
JOIN assignments a ON a.course_id = e.course_id
WHERE u.role = 'student'
  AND NOT EXISTS (
      SELECT 1
      FROM submissions s
      WHERE s.student_id = u.id
        AND s.assignment_id = a.id
        AND s.submitted_at <= a.due_date
  )
  AND a.due_date < NOW();
```

---

# CTE & Window Function Test Scenario

This query tests **CTEs, Window Functions (RANK), and Multi-level Aggregation**.

## Natural Language Query
> "For each course category, which course has the highest completion rate?"

## Expected Behavior
1.  **Thinking Process**: The model needs to compute completion rate per course (enrollments with progress = 100 / total enrollments), then rank courses within each category.
2.  **Clarification**: The model *might* ask what counts as "completed" (e.g., progress_pct = 100 vs. having a certificate). If so, answer "progress at 100%."
3.  **SQL Generation**: Should use a CTE for completion rates and a window function like `RANK()` or `ROW_NUMBER()` to pick the top per category.

## Reference SQL (MySQL 8+)
```sql
WITH completion_rates AS (
    SELECT
        cc.category_id,
        c.id AS course_id,
        c.title,
        COUNT(e.id) AS total_enrollments,
        SUM(CASE WHEN e.progress_pct = 100 THEN 1 ELSE 0 END) AS completions,
        ROUND(SUM(CASE WHEN e.progress_pct = 100 THEN 1 ELSE 0 END) * 100.0 / COUNT(e.id), 2) AS completion_rate
    FROM courses c
    JOIN course_categories cc ON cc.course_id = c.id
    JOIN enrollments e ON e.course_id = c.id
    GROUP BY cc.category_id, c.id, c.title
),
ranked AS (
    SELECT *,
        RANK() OVER (PARTITION BY category_id ORDER BY completion_rate DESC) AS rnk
    FROM completion_rates
)
SELECT
    category_id,
    course_id,
    title,
    total_enrollments,
    completions,
    completion_rate
FROM ranked
WHERE rnk = 1;
```

---

# Analytical / Business Logic Test Scenario

This query tests **Date Aggregation, Payment Status Filtering, and Trend Analysis**.

## Natural Language Query
> "Show me the monthly revenue breakdown for the last 6 months, including the number of transactions and the refund rate."

## Expected Behavior
1.  **Thinking Process**: The model should aggregate payments by month, filter by date range, compute total revenue from completed payments, count transactions, and calculate refund rate.
2.  **Clarification**: The model *might* ask about what "last 6 months" means relative to (e.g., current date vs. latest payment). If so, answer "From today's date."
3.  **SQL Generation**: Should use date functions (`DATE_FORMAT`, `DATE_SUB` or equivalent), conditional aggregation for refund rate, and `GROUP BY` month.

## Reference SQL (MySQL 8+)
```sql
SELECT
    DATE_FORMAT(p.created_at, '%Y-%m') AS month,
    COUNT(*) AS total_transactions,
    SUM(CASE WHEN p.status = 'completed' THEN p.amount ELSE 0 END) AS revenue,
    SUM(CASE WHEN p.status = 'refunded' THEN 1 ELSE 0 END) AS refunds,
    ROUND(SUM(CASE WHEN p.status = 'refunded' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS refund_rate_pct
FROM payments p
WHERE p.created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
GROUP BY DATE_FORMAT(p.created_at, '%Y-%m')
ORDER BY month DESC;
```
