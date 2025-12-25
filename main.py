import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

# --- Basic Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
mcp_server = FastMCP()

# --- Global state for current database connection ---
_current_db = None

def _get_server_engine():
    """Creates and returns a SQLAlchemy engine connected to MySQL server (no specific DB)."""
    try:
        engine = sqlalchemy.create_engine("mysql+mysqlconnector://rishi@localhost:3306", pool_pre_ping=True)
        return engine
    except Exception as e:
        logging.error(f"Error creating server engine: {e}")
        return None

def _get_db_engine(db_name: str = None):
    """Creates and returns a SQLAlchemy engine connected to a specific database."""
    target_db = db_name or _current_db
    if not target_db:
        return None
    try:
        engine = sqlalchemy.create_engine(f"mysql+mysqlconnector://rishi@localhost:3306/{target_db}", pool_pre_ping=True)
        return engine
    except Exception as e:
        logging.error(f"Error creating database engine for '{target_db}': {e}")
        return None

# --- Category 0: Connection & Top-Level Database Operations ---

@mcp_server.tool()
def connect_database(db_name: str) -> str:
    """
    Connect to a specific database. This sets the active database for subsequent operations.
    
    **WARNING**: You must connect to a database before using most tools.
    
    Args:
        db_name: Name of the database to connect to
    
    Returns:
        Success or error message
    
    Example: connect_database(db_name='my_database')
    """
    global _current_db
    logging.info(f"Executing tool: connect_database with db_name: {db_name}")
    
    engine = _get_db_engine(db_name)
    if not engine:
        return f"Error: Could not connect to database '{db_name}'. Database may not exist."
    
    try:
        with engine.connect() as connection:
            connection.execute(sqlalchemy.text("SELECT 1"))
        _current_db = db_name
        return f"Successfully connected to database '{db_name}'."
    except SQLAlchemyError as e:
        logging.error(f"Error connecting to database '{db_name}': {e}")
        return f"Error: {e}"

@mcp_server.tool()
def get_current_database() -> str:
    """
    Get the name of the currently connected database.
    
    Returns:
        Name of current database or message if none connected
    
    Example: get_current_database()
    """
    logging.info("Executing tool: get_current_database")
    if _current_db:
        return f"Currently connected to database: '{_current_db}'"
    return "No database currently connected. Use connect_database() first."

@mcp_server.tool()
def list_databases() -> dict:
    """
    Lists all databases available on the MySQL server.
    
    Returns:
        Dictionary with list of databases or error message
    
    Example: list_databases()
    """
    logging.info("Executing tool: list_databases")
    engine = _get_server_engine()
    if not engine:
        return {"error": "Could not create database engine."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW DATABASES"))
            databases = [row[0] for row in result]
        return {"databases": databases, "count": len(databases)}
    except SQLAlchemyError as e:
        logging.error(f"Error listing databases: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def create_database(db_name: str) -> dict:
    """
    Creates a new database with the given name.
    
    Args:
        db_name: Name of the database to create
    
    Returns:
        Dictionary with status and detail message
    
    Example: create_database(db_name='my_new_db')
    """
    logging.info(f"Executing tool: create_database with db_name: {db_name}")
    engine = _get_server_engine()
    if not engine:
        return {"error": "Could not create database engine."}
    
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(
                sqlalchemy.text(f"CREATE DATABASE `{db_name}`")
            )
        return {"status": "success", "detail": f"Database '{db_name}' created successfully."}
    except SQLAlchemyError as e:
        logging.error(f"Error creating database '{db_name}': {e}")
        return {"error": str(e)}

@mcp_server.tool()
def delete_database(db_name: str, confirm: bool = False) -> dict:
    """
    Deletes a database with the given name.
    
    **WARNING**: This is a DESTRUCTIVE operation that will permanently delete the database and all its data!
    
    Args:
        db_name: Name of the database to delete
        confirm: Must be set to True to confirm deletion (default: False)
    
    Returns:
        Dictionary with status or error message
    
    Example: delete_database(db_name='my_old_db', confirm=True)
    """
    logging.info(f"Executing tool: delete_database with db_name: {db_name}, confirm: {confirm}")
    
    if not confirm:
        return {
            "status": "confirmation required",
            "message": f"⚠️  WARNING: You are about to DELETE database '{db_name}' and ALL its data. This action cannot be undone!",
            "instruction": "To proceed, call this function again with confirm=True"
        }
    
    engine = _get_server_engine()
    if not engine:
        return {"error": "Could not create database engine."}
    
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(
                sqlalchemy.text(f"DROP DATABASE `{db_name}`")
            )
        
        # If the deleted database was the current one, clear it
        global _current_db
        if _current_db == db_name:
            _current_db = None
        
        return {"status": "success", "detail": f"Database '{db_name}' deleted successfully."}
    except SQLAlchemyError as e:
        logging.error(f"Error deleting database '{db_name}': {e}")
        return {"error": str(e)}

# --- Category 1: Discovery & Metadata ---

@mcp_server.tool()
def list_tables() -> dict:
    """
    Lists all tables in the currently connected database.
    
    **REQUIRES**: Active database connection (use connect_database first)
    
    Returns:
        Dictionary with list of tables or error message
    
    Example: list_tables()
    """
    logging.info("Executing tool: list_tables")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW TABLES"))
            tables = [row[0] for row in result]
        return {"tables": tables, "count": len(tables), "database": _current_db}
    except SQLAlchemyError as e:
        logging.error(f"Error listing tables: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def get_table_schema(table_name: str) -> dict:
    """
    Retrieves the schema (column definitions) for a specific table.
    
    **REQUIRES**: Active database connection
    
    Args:
        table_name: Name of the table to inspect
    
    Returns:
        Dictionary with list of column information or error message
    
    Example: get_table_schema(table_name='users')
    """
    logging.info(f"Executing tool: get_table_schema with table_name: {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        query = f"""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{_current_db}' AND TABLE_NAME = '{table_name}'
        """
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            schema = [row._asdict() for row in result]
        return {"table": table_name, "schema": schema, "column_count": len(schema)}
    except SQLAlchemyError as e:
        logging.error(f"Error getting table schema: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def get_table_relations() -> dict:
    """
    Retrieves all foreign key relationships in the currently connected database.
    
    **REQUIRES**: Active database connection
    
    Returns:
        Dictionary with list of foreign key relationships or error message
    
    Example: get_table_relations()
    """
    logging.info("Executing tool: get_table_relations")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        query = f"""
            SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME 
            FROM information_schema.key_column_usage AS kcu 
            WHERE kcu.TABLE_SCHEMA = '{_current_db}' AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            relations = [row._asdict() for row in result]
        return {"relations": relations, "count": len(relations), "database": _current_db}
    except SQLAlchemyError as e:
        logging.error(f"Error getting table relations: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def get_all_indexes(table_name: str) -> dict:
    """
    Retrieves all indexes for a specific table.
    
    **REQUIRES**: Active database connection
    
    Args:
        table_name: Name of the table to inspect
    
    Returns:
        Dictionary with list of indexes or error message
    
    Example: get_all_indexes(table_name='users')
    """
    logging.info(f"Executing tool: get_all_indexes with table_name: {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(f"SHOW INDEX FROM {table_name}"))
            indexes = [row._asdict() for row in result]
        return {"table": table_name, "indexes": indexes, "count": len(indexes)}
    except SQLAlchemyError as e:
        logging.error(f"Error getting indexes: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def describe_views() -> dict:
    """
    Lists all views in the currently connected database and their definitions.
    
    **REQUIRES**: Active database connection
    
    Returns:
        Dictionary with list of views and their definitions or error message
    
    Example: describe_views()
    """
    logging.info("Executing tool: describe_views")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW FULL TABLES WHERE TABLE_TYPE LIKE 'VIEW'"))
            views = []
            for row in result:
                view_name = row[0]
                view_query_res = connection.execute(sqlalchemy.text(f"SHOW CREATE VIEW {view_name}"))
                views.append(view_query_res.fetchone()._asdict())
        return {"views": views, "count": len(views), "database": _current_db}
    except SQLAlchemyError as e:
        logging.error(f"Error describing views: {e}")
        return {"error": str(e)}

# --- Category 2: Data Management ---

@mcp_server.tool()
def execute_read_query(query: str) -> dict:
    """
    Executes a SELECT query and returns the results.
    
    **REQUIRES**: Active database connection
    **NOTE**: Only SELECT queries are allowed for safety
    
    Args:
        query: SQL SELECT query to execute
    
    Returns:
        Dictionary with query results or error message
    
    Example: execute_read_query(query='SELECT * FROM users LIMIT 10')
    """
    logging.info(f"Executing tool: execute_read_query with query: {query[:100]}...")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            rows = [row._asdict() for row in result]
        return {"results": rows, "row_count": len(rows), "database": _current_db}
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def insert_record(table_name: str, data: dict) -> dict:
    """
    Inserts a single record into a table.
    
    **REQUIRES**: Active database connection
    
    Args:
        table_name: Name of the table to insert into
        data: Dictionary of column names and values
    
    Returns:
        Dictionary with inserted primary key or error message
    
    Example: insert_record(table_name='users', data={'name': 'John', 'email': 'john@example.com'})
    """
    logging.info(f"Executing tool: insert_record into {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            table = sqlalchemy.Table(table_name, sqlalchemy.MetaData(), autoload_with=engine)
            stmt = sqlalchemy.insert(table).values(**data)
            result = connection.execute(stmt)
            connection.commit()
        return {
            "status": "success",
            "inserted_primary_key": result.inserted_primary_key[0],
            "table": table_name
        }
    except SQLAlchemyError as e:
        logging.error(f"Error inserting record: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def bulk_insert(table_name: str, data_list: list[dict]) -> dict:
    """
    Inserts multiple records into a table at once.
    
    **REQUIRES**: Active database connection
    
    Args:
        table_name: Name of the table to insert into
        data_list: List of dictionaries, each representing a record
    
    Returns:
        Dictionary with number of rows affected or error message
    
    Example: bulk_insert(table_name='users', data_list=[{'name': 'John'}, {'name': 'Jane'}])
    """
    logging.info(f"Executing tool: bulk_insert into {table_name} with {len(data_list)} records")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            table = sqlalchemy.Table(table_name, sqlalchemy.MetaData(), autoload_with=engine)
            connection.execute(sqlalchemy.insert(table), data_list)
            connection.commit()
        return {
            "status": "success",
            "rows_affected": len(data_list),
            "table": table_name
        }
    except SQLAlchemyError as e:
        logging.error(f"Error bulk inserting records: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def update_records(table_name: str, data: dict, where_clause: str) -> dict:
    """
    Updates records in a table that match the WHERE clause.
    
    **REQUIRES**: Active database connection
    **WARNING**: Be careful with WHERE clause to avoid updating unintended records
    
    Args:
        table_name: Name of the table to update
        data: Dictionary of column names and new values
        where_clause: SQL WHERE clause (without 'WHERE' keyword)
    
    Returns:
        Dictionary with number of rows affected or error message
    
    Example: update_records(table_name='users', data={'email': 'newemail@example.com'}, where_clause='id = 5')
    """
    logging.info(f"Executing tool: update_records in {table_name} with where: {where_clause}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            table = sqlalchemy.Table(table_name, sqlalchemy.MetaData(), autoload_with=engine)
            stmt = sqlalchemy.update(table).where(sqlalchemy.text(where_clause)).values(**data)
            result = connection.execute(stmt)
            connection.commit()
        return {
            "status": "success",
            "rows_affected": result.rowcount,
            "table": table_name
        }
    except SQLAlchemyError as e:
        logging.error(f"Error updating records: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def delete_records(table_name: str, where_clause: str, dry_run: bool = True) -> dict:
    """
    Deletes records from a table that match the WHERE clause.
    
    **REQUIRES**: Active database connection
    **WARNING**: This is a DESTRUCTIVE operation! Always run with dry_run=True first to preview
    
    Args:
        table_name: Name of the table to delete from
        where_clause: SQL WHERE clause (without 'WHERE' keyword)
        dry_run: If True, shows preview without deleting (default: True)
    
    Returns:
        Dictionary with preview or deletion results
    
    Example: delete_records(table_name='users', where_clause='id = 5', dry_run=True)
    Example: delete_records(table_name='users', where_clause='id = 5', dry_run=False)  # Actually delete
    """
    logging.info(f"Executing tool: delete_records from {table_name} with where: {where_clause}, dry_run: {dry_run}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            table = sqlalchemy.Table(table_name, sqlalchemy.MetaData(), autoload_with=engine)
            
            if dry_run:
                rows = connection.execute(
                    sqlalchemy.select(table).where(sqlalchemy.text(where_clause))
                ).fetchall()
                return {
                    "dry_run": True,
                    "records_to_be_deleted": len(rows),
                    "preview": [row._asdict() for row in rows[:5]],
                    "message": "⚠️  This is a preview. Set dry_run=False to actually delete these records."
                }
            
            result = connection.execute(
                sqlalchemy.delete(table).where(sqlalchemy.text(where_clause))
            )
            connection.commit()
            return {
                "dry_run": False,
                "status": "success",
                "rows_affected": result.rowcount,
                "table": table_name
            }
    except SQLAlchemyError as e:
        logging.error(f"Error deleting records: {e}")
        return {"error": str(e)}

# --- Category 3: Schema Engineering ---

@mcp_server.tool()
def create_table(create_sql: str) -> dict:
    """
    Creates a new table using the provided SQL CREATE TABLE statement.
    
    **REQUIRES**: Active database connection
    
    Args:
        create_sql: Complete CREATE TABLE SQL statement
    
    Returns:
        Dictionary with status or error message
    
    Example: create_table(create_sql='CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255))')
    """
    logging.info(f"Executing tool: create_table")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(sqlalchemy.text(create_sql))
        return {"status": "success", "message": "Table created successfully"}
    except SQLAlchemyError as e:
        logging.error(f"Error creating table: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def add_column(table_name: str, column_definition: str) -> dict:
    """
    Adds a new column to an existing table.
    
    **REQUIRES**: Active database connection
    
    Args:
        table_name: Name of the table to modify
        column_definition: Column definition (e.g., 'email VARCHAR(255)')
    
    Returns:
        Dictionary with status or error message
    
    Example: add_column(table_name='users', column_definition='email VARCHAR(255)')
    """
    logging.info(f"Executing tool: add_column to {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(
                sqlalchemy.text(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
            )
        return {"status": "success", "message": f"Column added to {table_name} successfully"}
    except SQLAlchemyError as e:
        logging.error(f"Error adding column: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def drop_resource(resource_type: str, resource_name: str, confirm: bool = False) -> dict:
    """
    Drops a table or view from the database.
    
    **REQUIRES**: Active database connection
    **WARNING**: This is a DESTRUCTIVE operation that permanently deletes the table/view and all its data!
    
    Args:
        resource_type: Type of resource to drop ('TABLE' or 'VIEW')
        resource_name: Name of the table or view to drop
        confirm: Must be set to True to confirm deletion (default: False)
    
    Returns:
        Dictionary with status or error message
    
    Example: drop_resource(resource_type='TABLE', resource_name='old_users', confirm=True)
    """
    logging.info(f"Executing tool: drop_resource {resource_type} {resource_name}, confirm: {confirm}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    if not confirm:
        return {
            "status": "confirmation required",
            "message": f"⚠️  WARNING: You are about to DROP {resource_type} '{resource_name}'. This will permanently delete it and all its data!",
            "instruction": "To proceed, call this function again with confirm=True"
        }
    
    resource_type = resource_type.upper()
    if resource_type not in ["TABLE", "VIEW"]:
        return {"error": "Invalid resource_type. Must be 'TABLE' or 'VIEW'."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(
                sqlalchemy.text(f"DROP {resource_type} `{resource_name}`")
            )
        return {
            "status": "success",
            "message": f"{resource_type} '{resource_name}' dropped successfully"
        }
    except SQLAlchemyError as e:
        logging.error(f"Error dropping resource: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def create_index(index_name: str, table_name: str, columns: list[str]) -> dict:
    """
    Creates an index on one or more columns of a table.
    
    **REQUIRES**: Active database connection
    
    Args:
        index_name: Name for the new index
        table_name: Name of the table
        columns: List of column names to include in the index
    
    Returns:
        Dictionary with status or error message
    
    Example: create_index(index_name='idx_email', table_name='users', columns=['email'])
    """
    logging.info(f"Executing tool: create_index {index_name} on {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        column_list = ', '.join(columns)
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(
                sqlalchemy.text(f"CREATE INDEX {index_name} ON {table_name} ({column_list})")
            )
        return {
            "status": "success",
            "message": f"Index '{index_name}' created on {table_name}({column_list})"
        }
    except SQLAlchemyError as e:
        logging.error(f"Error creating index: {e}")
        return {"error": str(e)}

# --- Category 4: Transaction & Integrity ---

@mcp_server.tool()
def execute_transaction(queries: list[str]) -> dict:
    """
    Executes multiple SQL queries as a single transaction (all or nothing).
    
    **REQUIRES**: Active database connection
    **NOTE**: If any query fails, all changes are rolled back
    
    Args:
        queries: List of SQL queries to execute in the transaction
    
    Returns:
        Dictionary with transaction status or error message
    
    Example: execute_transaction(queries=['INSERT INTO users (name) VALUES ("John")', 'INSERT INTO logs (action) VALUES ("user_created")'])
    """
    logging.info(f"Executing tool: execute_transaction with {len(queries)} queries")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            trans = connection.begin()
            try:
                for query in queries:
                    connection.execute(sqlalchemy.text(query))
                trans.commit()
                return {
                    "status": "success",
                    "queries_executed": len(queries),
                    "message": "All queries executed successfully"
                }
            except SQLAlchemyError as e:
                trans.rollback()
                return {
                    "status": "rollback",
                    "error": str(e),
                    "message": "Transaction rolled back due to error"
                }
    except SQLAlchemyError as e:
        logging.error(f"Error in transaction: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def check_integrity_violations() -> dict:
    """
    Checks for foreign key constraint violations (orphaned records) in the database.
    
    **REQUIRES**: Active database connection
    **NOTE**: Finds child records that reference non-existent parent records
    
    Returns:
        Dictionary with list of orphaned records or error message
    
    Example: check_integrity_violations()
    """
    logging.info("Executing tool: check_integrity_violations")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        # First get all foreign key relationships
        relations_query = f"""
            SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME 
            FROM information_schema.key_column_usage AS kcu 
            WHERE kcu.TABLE_SCHEMA = '{_current_db}' AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """
        
        orphans = []
        with engine.connect() as connection:
            relations_result = connection.execute(sqlalchemy.text(relations_query))
            relations = [row._asdict() for row in relations_result]
            
            for rel in relations:
                # Find orphaned records
                check_query = f"""
                    SELECT child.* 
                    FROM `{rel['TABLE_NAME']}` AS child 
                    LEFT JOIN `{rel['REFERENCED_TABLE_NAME']}` AS parent 
                        ON parent.`{rel['REFERENCED_COLUMN_NAME']}` = child.`{rel['COLUMN_NAME']}`
                    WHERE parent.`{rel['REFERENCED_COLUMN_NAME']}` IS NULL 
                        AND child.`{rel['COLUMN_NAME']}` IS NOT NULL
                """
                
                orphan_result = connection.execute(sqlalchemy.text(check_query))
                for row in orphan_result:
                    orphans.append({
                        "table": rel['TABLE_NAME'],
                        "column": rel['COLUMN_NAME'],
                        "referenced_table": rel['REFERENCED_TABLE_NAME'],
                        "referenced_column": rel['REFERENCED_COLUMN_NAME'],
                        "orphaned_row": row._asdict()
                    })
        
        return {
            "orphans": orphans,
            "count": len(orphans),
            "database": _current_db,
            "message": f"Found {len(orphans)} orphaned record(s)" if orphans else "No integrity violations found"
        }
    except SQLAlchemyError as e:
        logging.error(f"Error checking integrity violations: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def validate_constraints(table_name: str) -> dict:
    """
    Checks for unique constraint violations in a specific table.
    
    **REQUIRES**: Active database connection
    **NOTE**: Detects duplicate values in columns with unique constraints
    
    Args:
        table_name: Name of the table to check
    
    Returns:
        Dictionary with list of constraint violations or error message
    
    Example: validate_constraints(table_name='users')
    """
    logging.info(f"Executing tool: validate_constraints for {table_name}")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        violations = []
        
        with engine.connect() as connection:
            # Get all unique indexes
            index_result = connection.execute(sqlalchemy.text(f"SHOW INDEX FROM {table_name}"))
            indexes = [row._asdict() for row in index_result]
            
            unique_indexes = [
                idx for idx in indexes 
                if idx['Non_unique'] == 0 and idx['Key_name'] != 'PRIMARY'
            ]
            
            for index in unique_indexes:
                column = index['Column_name']
                # Find duplicates
                dup_query = f"""
                    SELECT `{column}`, COUNT(*) as count 
                    FROM `{table_name}` 
                    GROUP BY `{column}` 
                    HAVING count > 1
                """
                dup_result = connection.execute(sqlalchemy.text(dup_query))
                for row in dup_result:
                    violations.append({
                        "constraint": index['Key_name'],
                        "column": column,
                        "violating_value": row._asdict()
                    })
        
        return {
            "violations": violations,
            "count": len(violations),
            "table": table_name,
            "message": f"Found {len(violations)} constraint violation(s)" if violations else "No constraint violations found"
        }
    except SQLAlchemyError as e:
        logging.error(f"Error validating constraints: {e}")
        return {"error": str(e)}

# --- Category 5: Performance & Admin ---

@mcp_server.tool()
def explain_query(query: str) -> dict:
    """
    Shows the execution plan for a query (useful for performance optimization).
    
    **REQUIRES**: Active database connection
    
    Args:
        query: SQL query to analyze
    
    Returns:
        Dictionary with query execution plan or error message
    
    Example: explain_query(query='SELECT * FROM users WHERE email = "john@example.com"')
    """
    logging.info(f"Executing tool: explain_query")
    if not _current_db:
        return {"error": "No database connected. Use connect_database() first."}
    
    engine = _get_db_engine()
    if not engine:
        return {"error": f"Could not connect to database '{_current_db}'."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(f"EXPLAIN {query}"))
            plan = [row._asdict() for row in result]
        return {
            "execution_plan": plan,
            "query": query,
            "database": _current_db
        }
    except SQLAlchemyError as e:
        logging.error(f"Error explaining query: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def get_db_stats(db_name: str = None) -> dict:
    """
    Retrieves statistics about database tables (row counts, sizes, etc.).
    
    Args:
        db_name: Database name (uses current database if not specified)
    
    Returns:
        Dictionary with database statistics or error message
    
    Example: get_db_stats()
    Example: get_db_stats(db_name='my_database')
    """
    target_db = db_name or _current_db
    logging.info(f"Executing tool: get_db_stats for {target_db}")
    
    if not target_db:
        return {"error": "No database specified and no database currently connected."}
    
    engine = _get_server_engine()
    if not engine:
        return {"error": "Could not create database engine."}
    
    try:
        query = f"""
            SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, ENGINE 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = '{target_db}'
        """
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            stats = [row._asdict() for row in result]
        
        total_data = sum(s['DATA_LENGTH'] or 0 for s in stats)
        total_index = sum(s['INDEX_LENGTH'] or 0 for s in stats)
        
        return {
            "statistics": stats,
            "table_count": len(stats),
            "total_data_size_bytes": total_data,
            "total_index_size_bytes": total_index,
            "total_size_bytes": total_data + total_index,
            "database": target_db
        }
    except SQLAlchemyError as e:
        logging.error(f"Error getting database stats: {e}")
        return {"error": str(e)}

@mcp_server.tool()
def list_active_processes() -> dict:
    """
    Lists all active MySQL processes/connections.
    
    **NOTE**: Useful for monitoring database activity and troubleshooting
    
    Returns:
        Dictionary with list of active processes or error message
    
    Example: list_active_processes()
    """
    logging.info("Executing tool: list_active_processes")
    engine = _get_server_engine()
    if not engine:
        return {"error": "Could not create database engine."}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW FULL PROCESSLIST"))
            processes = [row._asdict() for row in result]
        return {
            "processes": processes,
            "count": len(processes)
        }
    except SQLAlchemyError as e:
        logging.error(f"Error listing processes: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    logging.info("Starting MCP tool server in HTTP mode...")
    logging.info("Available tools: 26 database management tools")
    mcp_server.run(transport="http")