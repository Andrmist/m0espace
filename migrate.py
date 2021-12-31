from db import pool

conn = pool.get_connection()
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                      token varchar(25) NOT NULL UNIQUE PRIMARY KEY,
                      name varchar(32) DEFAULT 'guest',
                      ip varchar(15) DEFAULT NULL,
                      discord_id varchar(18) DEFAULT NULL
                  )""")

cursor.execute("""CREATE TABLE IF NOT EXISTS files (
                      id varchar(12) NOT NULL UNIQUE PRIMARY KEY,
                      user varchar(25) NOT NULL,
                      ext varchar(12) NOT NULL,
                      upload_date TIMESTAMP NOT NULL DEFAULT current_timestamp(),
                      mimetype varchar(32) NOT NULL,
                      size bigint NOT NULL
                  )""")
