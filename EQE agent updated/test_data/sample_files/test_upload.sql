-- 1. Setup: Remove existing table if it exists to start fresh
DROP TABLE IF EXISTS employees;

-- 2. Create: Define the table structure (Schema)
CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    hire_date DATE,
    salary DECIMAL(10, 2)
);

-- 3. Insert: Add sample data into the table
INSERT INTO employees (first_name, last_name, email, hire_date, salary)
VALUES 
    ('Alice', 'Johnson', 'alice.j@example.com', '2023-01-15', 75000.00),
    ('Bob', 'Smith', 'bob.s@example.com', '2022-11-03', 62000.50),
    ('Charlie', 'Davis', 'charlie.d@example.com', '2024-02-20', 58000.00);

-- 4. Query: Verify the data was added
SELECT * FROM employees WHERE salary > 60000;