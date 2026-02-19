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
