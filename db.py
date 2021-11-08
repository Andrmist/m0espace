"""Database connection for m0e"""
import mariadb
import config


connection = mariadb.connect(
    user=config.mariadb["user"],
    password=config.mariadb["pass"],
    host=config.mariadb["host"],
    port=config.mariadb["port"],
    database=config.mariadb["database"],
    autocommit=True)

cursor = connection.cursor()

