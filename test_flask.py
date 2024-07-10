from flask import Flask
from test_bed import Session
from sqlalchemy import select
from TI_TimeTracker_DB_api import Games, Users, Factions, Events

#config=dotenv_values(".env")

app = Flask(__name__)
#app.config["SQLALCHEMY_DATABSE_URI"]="mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db'])

@app.route("/")
def hello_world():
	with Session() as session:
		return "<p>Hello, World %s!</p>"%session.scalars(select(Users).where(Users.UserID==1)).first().UserName