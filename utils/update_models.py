import psycopg2
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
import os

# Database connection details
DB_NAME = "sworn"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"  # Change if needed
DB_PORT = "5433"  # Default PostgreSQL port

# Connect to PostgreSQL
def get_table_schema():
    connection = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cursor = connection.cursor()

    # Fetch table names
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
    )
    tables = cursor.fetchall()

    table_schemas = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(
            f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = '{table_name}';"
        )
        columns = cursor.fetchall()
        table_schemas[table_name] = columns

    cursor.close()
    connection.close()
    return table_schemas


# Map PostgreSQL types to SQLAlchemy types
def map_postgres_to_sqlalchemy(pg_type):
    mapping = {
        "integer": "Integer",
        "bigint": "Integer",
        "smallint": "Integer",
        "serial": "Integer",
        "text": "Text",
        "character varying": "String",
        "varchar": "String",
        "character": "String",
        "boolean": "Boolean",
        "double precision": "Float",
        "numeric": "Float",
        "real": "Float",
        "timestamp without time zone": "DateTime",
        "timestamp with time zone": "DateTime",
        "date": "DateTime",
    }
    return mapping.get(pg_type, "String")  # Default to String if unknown


# Generate SQLAlchemy models
def generate_models(table_schemas):
    models_code = """from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()\n\n"""

    for table, columns in table_schemas.items():
        class_name = "".join(word.capitalize() for word in table.split("_"))
        models_code += f"class {class_name}(Base):\n"
        models_code += f"    __tablename__ = '{table}'\n"

        for column in columns:
            col_name, col_type, is_nullable, col_default = column
            sa_type = map_postgres_to_sqlalchemy(col_type)
            nullable = "nullable=True" if is_nullable == "YES" else "nullable=False"
            models_code += f"    {col_name} = Column({sa_type}, {nullable})\n"

        models_code += "\n"

    return models_code


# Write to models/core.py
def write_to_file(content):
    os.makedirs("models", exist_ok=True)
    with open("models/core.py", "w") as file:
        file.write(content)
    print("✅ models/core.py has been updated!")


if __name__ == "__main__":
    table_schemas = get_table_schema()
    models_content = generate_models(table_schemas)
    write_to_file(models_content)
