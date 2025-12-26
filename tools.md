# DBMS Agent Tools

This document outlines the tools available in the DBMS MCP Agent.

---

## Category 0: Connection & Top-Level Database Operations

### `connect_database(db_name: str) -> str`
Connect to a specific database. This sets the active database for subsequent operations.

**WARNING**: You must connect to a database before using most tools.

- **Args**:
  - `db_name` (str): Name of the database to connect to.
- **Returns**: Success or error message.
- **Example**: `connect_database(db_name='my_database')`

### `get_current_database() -> str`
Get the name of the currently connected database.

- **Returns**: Name of current database or message if none connected.
- **Example**: `get_current_database()`

### `list_databases() -> dict`
Lists all databases available on the MySQL server.

- **Returns**: Dictionary with list of databases or error message.
- **Example**: `list_databases()`

### `create_database(db_name: str) -> dict`
Creates a new database with the given name.

- **Args**:
  - `db_name` (str): Name of the database to create.
- **Returns**: Dictionary with status and detail message.
- **Example**: `create_database(db_name='my_new_db')`

### `delete_database(db_name: str, confirm: bool = False) -> dict`
Deletes a database with the given name.

**WARNING**: This is a DESTRUCTIVE operation that will permanently delete the database and all its data!

- **Args**:
  - `db_name` (str): Name of the database to delete.
  - `confirm` (bool): Must be set to `True` to confirm deletion (default: `False`).
- **Returns**: Dictionary with status or error message.
- **Example**: `delete_database(db_name='my_old_db', confirm=True)`

---

## Category 1: Discovery & Metadata

### `list_tables() -> dict`
Lists all tables in the currently connected database.

**REQUIRES**: Active database connection.

- **Returns**: Dictionary with list of tables or error message.
- **Example**: `list_tables()`

### `get_table_schema(table_name: str) -> dict`
Retrieves the schema (column definitions) for a specific table.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to inspect.
- **Returns**: Dictionary with list of column information or error message.
- **Example**: `get_table_schema(table_name='users')`

### `get_table_relations() -> dict`
Retrieves all foreign key relationships in the currently connected database.

**REQUIRES**: Active database connection.

- **Returns**: Dictionary with list of foreign key relationships or error message.
- **Example**: `get_table_relations()`

### `get_full_schema() -> dict`
Retrieves a complete schema overview for the currently connected database, including tables, schemas, and relationships.

**REQUIRES**: Active database connection.

- **Returns**: A dictionary containing the full database schema or an error message.
- **Example**: `get_full_schema()`

### `get_all_indexes(table_name: str) -> dict`
Retrieves all indexes for a specific table.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to inspect.
- **Returns**: Dictionary with list of indexes or error message.
- **Example**: `get_all_indexes(table_name='users')`

### `describe_views() -> dict`
Lists all views in the currently connected database and their definitions.

**REQUIRES**: Active database connection.

- **Returns**: Dictionary with list of views and their definitions or error message.
- **Example**: `describe_views()`

---

## Category 2: Data Management

### `execute_read_query(query: str) -> dict`
Executes a `SELECT` query and returns the results.

**REQUIRES**: Active database connection.
**NOTE**: Only `SELECT` queries are allowed for safety.

- **Args**:
  - `query` (str): SQL `SELECT` query to execute.
- **Returns**: Dictionary with query results or error message.
- **Example**: `execute_read_query(query='SELECT * FROM users LIMIT 10')`

### `insert_record(table_name: str, data: dict) -> dict`
Inserts a single record into a table.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to insert into.
  - `data` (dict): Dictionary of column names and values.
- **Returns**: Dictionary with inserted primary key or error message.
- **Example**: `insert_record(table_name='users', data={'name': 'John', 'email': 'john@example.com'})`

### `bulk_insert(table_name: str, data_list: list[dict]) -> dict`
Inserts multiple records into a table at once.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to insert into.
  - `data_list` (list[dict]): List of dictionaries, each representing a record.
- **Returns**: Dictionary with number of rows affected or error message.
- **Example**: `bulk_insert(table_name='users', data_list=[{'name': 'John'}, {'name': 'Jane'}])`

### `update_records(table_name: str, data: dict, where_clause: str) -> dict`
Updates records in a table that match the `WHERE` clause.

**REQUIRES**: Active database connection.
**WARNING**: Be careful with `WHERE` clause to avoid updating unintended records.

- **Args**:
  - `table_name` (str): Name of the table to update.
  - `data` (dict): Dictionary of column names and new values.
  - `where_clause` (str): SQL `WHERE` clause (without 'WHERE' keyword).
- **Returns**: Dictionary with number of rows affected or error message.
- **Example**: `update_records(table_name='users', data={'email': 'newemail@example.com'}, where_clause='id = 5')`

### `delete_records(table_name: str, where_clause: str, dry_run: bool = True) -> dict`
Deletes records from a table that match the `WHERE` clause.

**REQUIRES**: Active database connection.
**WARNING**: This is a DESTRUCTIVE operation! Always run with `dry_run=True` first to preview.

- **Args**:
  - `table_name` (str): Name of the table to delete from.
  - `where_clause` (str): SQL `WHERE` clause (without 'WHERE' keyword).
  - `dry_run` (bool): If True, shows preview without deleting (default: True).
- **Returns**: Dictionary with preview or deletion results.
- **Example**: `delete_records(table_name='users', where_clause='id = 5', dry_run=False)`

---

## Category 3: Schema Engineering

### `create_table(create_sql: str) -> dict`
Creates a new table using the provided `CREATE TABLE` statement.

**REQUIRES**: Active database connection.

- **Args**:
  - `create_sql` (str): Complete `CREATE TABLE` SQL statement.
- **Returns**: Dictionary with status or error message.
- **Example**: `create_table(create_sql='CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255))')`

### `add_column(table_name: str, column_definition: str) -> dict`
Adds a new column to an existing table.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to modify.
  - `column_definition` (str): Column definition (e.g., 'email VARCHAR(255)').
- **Returns**: Dictionary with status or error message.
- **Example**: `add_column(table_name='users', column_definition='email VARCHAR(255)')`

### `drop_resource(resource_type: str, resource_name: str, confirm: bool = False) -> dict`
Drops a table or view from the database.

**REQUIRES**: Active database connection.
**WARNING**: This is a DESTRUCTIVE operation!

- **Args**:
  - `resource_type` (str): Type of resource to drop ('TABLE' or 'VIEW').
  - `resource_name` (str): Name of the table or view to drop.
  - `confirm` (bool): Must be set to `True` to confirm deletion.
- **Returns**: Dictionary with status or error message.
- **Example**: `drop_resource(resource_type='TABLE', resource_name='old_users', confirm=True)`

### `create_index(index_name: str, table_name: str, columns: list[str]) -> dict`
Creates an index on one or more columns of a table.

**REQUIRES**: Active database connection.

- **Args**:
  - `index_name` (str): Name for the new index.
  - `table_name` (str): Name of the table.
  - `columns` (list[str]): List of column names to include in the index.
- **Returns**: Dictionary with status or error message.
- **Example**: `create_index(index_name='idx_email', table_name='users', columns=['email'])`

---

## Category 4: Transaction & Integrity

### `execute_transaction(queries: list[str]) -> dict`
Executes multiple SQL queries as a single transaction (all or nothing).

**REQUIRES**: Active database connection.

- **Args**:
  - `queries` (list[str]): List of SQL queries to execute.
- **Returns**: Dictionary with transaction status or error message.
- **Example**: `execute_transaction(queries=['INSERT ...', 'UPDATE ...'])`

### `check_integrity_violations() -> dict`
Checks for foreign key constraint violations (orphaned records).

**REQUIRES**: Active database connection.

- **Returns**: Dictionary with list of orphaned records or error message.
- **Example**: `check_integrity_violations()`

### `validate_constraints(table_name: str) -> dict`
Checks for unique constraint violations in a specific table.

**REQUIRES**: Active database connection.

- **Args**:
  - `table_name` (str): Name of the table to check.
- **Returns**: Dictionary with list of constraint violations or error message.
- **Example**: `validate_constraints(table_name='users')`

---

## Category 5: Performance & Admin

### `explain_query(query: str) -> dict`
Shows the execution plan for a query.

**REQUIRES**: Active database connection.

- **Args**:
  - `query` (str): SQL query to analyze.
- **Returns**: Dictionary with query execution plan or error message.
- **Example**: `explain_query(query='SELECT * FROM users WHERE email = "a@b.com"')`

### `get_db_stats(db_name: str = None) -> dict`
Retrieves statistics about database tables (row counts, sizes, etc.).

- **Args**:
  - `db_name` (str): Database name (uses current database if not specified).
- **Returns**: Dictionary with database statistics or error message.
- **Example**: `get_db_stats()`

### `list_active_processes() -> dict`
Lists all active MySQL processes/connections.

- **Returns**: Dictionary with list of active processes or error message.
- **Example**: `list_active_processes()`

---

## Category 6: Visualization

### `visualize_schema(output_dir: str = "schemaspy_output") -> dict`
Generates a detailed schema analysis and ER diagram using SchemaSpy.

**REQUIRES**: Active database connection, Java, Graphviz, `schemaspy-app.jar`, and `mysql-connector-java.jar`.

- **Args**:
  - `output_dir` (str): The directory to save the report to (default: `schemaspy_output`).
- **Returns**: Dictionary with status and a detail message.
- **Example**: `visualize_schema()`
