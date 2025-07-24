from sqlalchemy import URL, make_url

database_driver = input("database driver? ")
username = input("username? ")
password = input("password? ")
host = input("host? ")
port = input("port? ")
database = input("database? ")

sqlalchemy_url = URL.create(
    drivername=database_driver,
    username=username,
    password=password,
    host=host,
    port=int(port),
    database=database,
)

stringified_sqlalchemy_url = sqlalchemy_url.render_as_string(
    hide_password=False
)

# assert make_url round trip
assert make_url(stringified_sqlalchemy_url) == sqlalchemy_url

print(
    f"The correctly escaped string that can be passed "
    f"to SQLAlchemy make_url() and create_engine() is:"
    f"\n\n     {stringified_sqlalchemy_url!r}\n"
)

percent_replaced_url = stringified_sqlalchemy_url.replace("%", "%%")

# assert percent-interpolated plus make_url round trip
assert make_url(percent_replaced_url % {}) == sqlalchemy_url

print(
    f"The SQLAlchemy URL that can be placed in a ConfigParser "
    f"file such as alembic.ini is:\n\n      "
    f"sqlalchemy.url = {percent_replaced_url}\n"
)