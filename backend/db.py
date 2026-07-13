import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="military_planner",
        user="postgres",
        password="your_password_here"
    )