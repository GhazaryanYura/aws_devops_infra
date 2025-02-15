import psycopg2
from psycopg2 import sql
import os

# Use environment variables to securely pass sensitive data
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "api_db"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "mi_urishTIPISecureP4ssw0rd"),
    "host": os.getenv("DB_HOST", "postgres-for-academy.cregwuq226t4.us-east-1.rds.amazonaws.com"),
    "port": os.getenv("DB_PORT", "5432"),
}

MIGRATIONS_FOLDER = "./migrations"  # Migrations folder packaged with the Lambda function


def check_migrations_table_exists(conn):
    """Check and create the migrations table if it doesn't exist."""
    with conn.cursor() as cursor:
        query = sql.SQL(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'migrations'
            );
            """
        )
        cursor.execute(query)
        result = cursor.fetchone()[0]

        if not result:
            print("Creating migrations table")
            create_table_query = sql.SQL(
                """
                CREATE TABLE migrations (
                    migration_name VARCHAR NOT NULL
                );
                """
            )
            cursor.execute(create_table_query)
            conn.commit()
            print("Migrations table created successfully")


def apply_pending_migrations(conn):
    """Apply migrations that haven't been executed yet."""
    with conn.cursor() as cursor:
        # Get the list of already applied migrations
        cursor.execute("SELECT migration_name FROM migrations;")
        applied_migrations = {row[0] for row in cursor.fetchall()}

        # Get the list of migration files from the migrations folder
        migration_files = sorted(os.listdir(MIGRATIONS_FOLDER))

        for migration_file in migration_files:
            if migration_file not in applied_migrations:
                print(f"Applying migration: {migration_file}")

                # Read and execute the migration file
                with open(os.path.join(MIGRATIONS_FOLDER, migration_file), "r") as file:
                    migration_sql = file.read()
                    cursor.execute(migration_sql)

                # Add the migration file to the migrations table
                cursor.execute(
                    "INSERT INTO migrations (migration_name) VALUES (%s);",
                    (migration_file,),
                )
                conn.commit()
                print(f"Migration {migration_file} applied successfully")
            else:
                print(f"Skipping already applied migration: {migration_file}")


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            # Check and create the migrations table if it doesn't exist
            check_migrations_table_exists(conn)

            # Apply pending migrations
            apply_pending_migrations(conn)

        return {
            "statusCode": 200,
            "body": "Migrations applied successfully",
        }

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return {
            "statusCode": 500,
            "body": f"Database error: {e}",
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "body": f"Unexpected error: {e}",
        }
