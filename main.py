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

# --- Database Tools ---

def _get_engine():
    """Creates and returns a SQLAlchemy engine."""
    try:
        engine = sqlalchemy.create_engine("mysql+mysqlconnector://rishi@localhost:3306", pool_pre_ping=True)
        return engine
    except Exception as e:
        logging.error(f"Error creating database engine: {e}")
        return None

@mcp_server.tool()
def list_databases() -> list[str]:
    """Lists all databases available on the MySQL server."""
    logging.info("Executing tool: list_databases")
    engine = _get_engine()
    if not engine:
        return ["Error: Could not create database engine."]
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW DATABASES"))
            databases = [row[0] for row in result]
            return databases
    except SQLAlchemyError as e:
        logging.error(f"An error occurred while listing databases: {e}")
        return [f"Error: {e}"]

@mcp_server.tool()
def create_database(db_name: str) -> str:
    """Creates a new database with the given name. Example: create_database(db_name='my_new_db')"""
    logging.info(f"Executing tool: create_database with db_name: {db_name}")
    engine = _get_engine()
    if not engine:
        return "Error: Could not create database engine."
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(sqlalchemy.text(f"CREATE DATABASE {db_name}"))
        return f"Database '{db_name}' created successfully."
    except SQLAlchemyError as e:
        logging.error(f"An error occurred while creating database '{db_name}': {e}")
        return f"Error: {e}"

@mcp_server.tool()
def delete_database(db_name: str) -> str:
    """Deletes a database with the given name. Example: delete_database(db_name='my_old_db')"""
    logging.info(f"Executing tool: delete_database with db_name: {db_name}")
    engine = _get_engine()
    if not engine:
        return "Error: Could not create database engine."
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(sqlalchemy.text(f"DROP DATABASE {db_name}"))
        return f"Database '{db_name}' deleted successfully."
    except SQLAlchemyError as e:
        logging.error(f"An error occurred while deleting database '{db_name}': {e}")
        return f"Error: {e}"

if __name__ == "__main__":
    logging.info("Starting MCP tool server in HTTP mode...")
    mcp_server.run(transport="http")
