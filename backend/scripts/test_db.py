import pymysql
try:
    print("Connecting to MySQL...")
    conn = pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="kunj@2006",
        database="live_trace_dashboard",
        connect_timeout=3
    )
    print("Success!")
    conn.close()
except Exception as e:
    print("Error:", e)
