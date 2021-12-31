"""Database connection for m0e"""
import mariadb
import config


pool = mariadb.ConnectionPool(
    user=config.mariadb["user"],
    password=config.mariadb["pass"],
    host=config.mariadb["host"],
    port=config.mariadb["port"],
    database=config.mariadb["database"],
    autocommit=True,
    pool_name="moe",
    pool_size=15)

