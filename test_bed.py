#used for testing the tables and various functions prior to putting it in the page
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import datetime as dt

gdate=dt.date.today().strftime("%Y%m%d")
UF_Dict={"Hythem":("Yssaril Tribes",2),"Charlie":("VuilRaith Cabal",1), "GRRN":("Nekro Virus",4), "Jakers":("Council Keleres",3),
		"Sunny":("Barony of Letnev",6),"Nathan":("Naaz-Rohka Alliance",5)}
Session=sessionmaker(engine)

def createGame():
	with Session()as session:
		newGame=Games(GameDate=gdate)
		session.add(newGame)
		session.commit()

def createUsers():
	with Session() as session:
		session.add(Users(UserName="Charlie"))
		session.add(Users(UserName="Nathan"))
		session.add(Users(UserName="Sunny"))
		session.add(Users(UserName="GRRN"))
		session.add(Users(UserName="Jakers"))
		session.add(Users(UserName="Hythem"))
		session.commit()
		
def createFactions():
	with Session() as session:
			GID=session.scalars(select(Games).where(Games.GameDate==gdate)).first().GameID
			
			for key in UF_Dict.keys():
					session.add(Factions(FactionName=UF_Dict[key][0], 
						UserID=session.scalars(select(Users).where(Users.UserName==key)).first().UserID, 
						GameID=GID,TableOrder=UF_Dict[key][1]))
			session.commit()
			'''session.add(Factions(FactionName="VuilRaith Cabal", 
			UserID=session.scalars(select(Users).where(Users.UserName=="Charlie")).first().UserID, 
			GameID=GID,TableOrder=2))
			session.add(Factions(FactionName="Yssaril Tribes", 
			UserID=session.scalars(select(Users).where(Users.UserName=="Hythem")).first().UserID, 
			GameID=GID,TableOrder=2))
			session.add(Factions(FactionName="Yssaril Tribes", 
			UserID=session.scalars(select(Users).where(Users.UserName=="Hythem")).first().UserID, 
			GameID=GID,TableOrder=2))
			session.add(Factions(FactionName="Yssaril Tribes", 
			UserID=session.scalars(select(Users).where(Users.UserName=="Hythem")).first().UserID, 
			GameID=GID,TableOrder=2))
			session.add(Factions(FactionName="Yssaril Tribes", 
			UserID=session.scalars(select(Users).where(Users.UserName=="Hythem")).first().UserID, 
			GameID=GID,TableOrder=2))
			'''


#createGame()
#createUsers()
createFactions()