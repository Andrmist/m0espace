## Moe space

Moe space - simple and lightweight file hosting written on Python and uses Flask and MariaDB database.

By default, uses simple token and Discord authorization (you can easily disable it) 

## Install

```shell
git clone https://github.com/Andrmist/m0espace
pip3 install -r requirements.txt
python3 migrate.py
```
Use with uWSGI.
Example configuration file for uWSGI stored in [m0espace.ini](m0espace.ini)

## Configuration

Example of config stored in [config.example.py](config.example.py)
