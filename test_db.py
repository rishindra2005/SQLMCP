import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

def get_engine():
    """Creates and returns a SQLAlchemy engine."""
    try:
        # The URL format is dialect+driver://username:password@host:port/
        # No database is specified in the URL because we need to create/delete databases.
        engine = sqlalchemy.create_engine("mysql+mysqlconnector://rishi@localhost:3306")
        return engine
    except Exception as e:
        print(f"Error creating database engine: {e}")
        return None

def list_databases(engine):
    """Lists all databases on the server."""
    try:
        with engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("SHOW DATABASES"))
            databases = [row[0] for row in result]
            return databases
    except SQLAlchemyError as e:
        print(f"An error occurred while listing databases: {e}")
        return []

def create_database(engine, db_name):
    """Creates a new database."""
    try:
        with engine.connect() as connection:
            # Use .execution_options(autocommit=True) for DDL statements
            connection.execution_options(autocommit=True).execute(sqlalchemy.text(f"CREATE DATABASE {db_name}"))
        print(f"Database '{db_name}' created successfully.")
        return True
    except SQLAlchemyError as e:
        print(f"An error occurred while creating database '{db_name}': {e}")
        return False

def delete_database(engine, db_name):
    """Deletes a database."""
    try:
        with engine.connect() as connection:
            connection.execution_options(autocommit=True).execute(sqlalchemy.text(f"DROP DATABASE {db_name}"))
        print(f"Database '{db_name}' deleted successfully.")
        return True
    except SQLAlchemyError as e:
        print(f"An error occurred while deleting database '{db_name}': {e}")
        return False

if __name__ == "__main__":
    test_db_name = "test_mcp_db_12345"  # Using a unique name to avoid conflicts
    engine = get_engine()

    if engine:
        print("--- Database Test Script ---")
        
        # Use a try...finally block to ensure cleanup
        try:
            # 1. Initial state
            print("\n1. Listing initial databases...")
            initial_dbs = list_databases(engine)
            print(f"   Databases found: {initial_dbs}")
            if test_db_name in initial_dbs:
                print(f"   Warning: Test database '{test_db_name}' already exists. Attempting to delete it.")
                delete_database(engine, test_db_name)

            # 2. Create database
            print(f"\n2. Creating test database '{test_db_name}'...")
            create_database(engine, test_db_name)

            # 3. Verify creation
            print("\n3. Listing databases after creation...")
            dbs_after_create = list_databases(engine)
            print(f"   Databases found: {dbs_after_create}")
            if test_db_name in dbs_after_create:
                print(f"   Success: Test database '{test_db_name}' was created.")
            else:
                print(f"   Failure: Test database '{test_db_name}' was NOT created.")

        except Exception as e:
            print(f"\nAn unexpected error occurred during the test: {e}")

        finally:
            # 4. Cleanup
            print(f"\n4. Deleting test database '{test_db_name}'...")
            delete_database(engine, test_db_name)

            # 5. Verify deletion
            print("\n5. Listing databases after deletion...")
            dbs_after_delete = list_databases(engine)
            print(f"   Databases found: {dbs_after_delete}")
            if test_db_name not in dbs_after_delete:
                print(f"   Success: Test database '{test_db_name}' was deleted.")
            else:
                print(f"   Failure: Test database '{test_db_name}' was NOT deleted.")
            
            print("\n--- Test Finished ---")
