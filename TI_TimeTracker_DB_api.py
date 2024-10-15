
import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, create_engine, DateTime
from sqlalchemy.orm import declarative_base, relationship, mapped_column, Mapped
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql import func
from dotenv import dotenv_values
#define the MARIADB engine

config=dotenv_values(".env")	#laod the envinronment variabls
engine=create_engine("mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db']))	#create the engine for connection
Base=declarative_base()

class Games(Base):
	__tablename__="games"
	#keys
	GameID: Mapped[int]=mapped_column(primary_key=True)
	#data
	GamePhase: Mapped[str]=mapped_column(String(30), default="Setup")
	GameState: Mapped[str]=mapped_column(String(30), default="Active")
	GameRound: Mapped[int]=mapped_column(default=0)
	GameDate: Mapped[datetime.date]
	GameWinner: Mapped[Optional[str]]=mapped_column(String(30))
	Active: Mapped[bool] =mapped_column(default=0)	#if active game: 1
	#relationship
	GameFactions: Mapped[List["Factions"]]=relationship(back_populates="GamePlayed")
	GameEvents: Mapped[List["Events"]]=relationship(back_populates="Game")	

	GameCombats: Mapped[List["Combats"]]=relationship(back_populates="Game")	#backlink to combats table

	
class Users(Base):
	__tablename__="users"
	#keys
	UserID: Mapped[int]=mapped_column(primary_key=True)
	#data
	UserName: Mapped[str]=mapped_column(String(30), unique=True)
	#relationships
	FactionsPlayed: Mapped[List["Factions"]]=relationship(back_populates="User")
	

class Factions(Base):
	__tablename__="factions"
	#keys
	FactionName: Mapped[str]=mapped_column(String(50))
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	UserID: Mapped[int] = mapped_column(ForeignKey("users.UserID"))
	#data
	Active: Mapped[bool] =mapped_column(default=0)
	TableOrder: Mapped[int] =mapped_column(default=0)
	Speaker: Mapped[bool] =mapped_column(default=0)
	Initiative: Mapped[int] =mapped_column(default=0)
	TotalTime: Mapped[datetime.timedelta] =mapped_column(default=datetime.timedelta(seconds=0))
	Pass: Mapped[bool]=mapped_column(default=0)
	Score: Mapped[int]=mapped_column(default=0)
	#relationships
	GamePlayed: Mapped["Games"]=relationship(back_populates="GameFactions")
	User: Mapped["Users"]=relationship(back_populates="FactionsPlayed")
	FactionActions: Mapped[List["Events"]]=relationship(back_populates="Faction")#is this right?
	#constraints
	PrimaryKeyConstraint(FactionName,GameID,name="pk_factions")

class Events(Base):
	__tablename__="events"
	#keys
	EventID: Mapped[int] = mapped_column(primary_key=True)
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	FactionName: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	#data
	EventTime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
	EventType: Mapped[str]=mapped_column(String(30))
	MiscData: Mapped[Optional[int]]
	PhaseData: Mapped[Optional[str]]=mapped_column(String(30))
	StateData: Mapped[Optional[str]]=mapped_column(String(30))
	#relationships
	Game: Mapped["Games"]=relationship(back_populates="GameEvents")
	Faction: Mapped["Factions"]=relationship(back_populates="FactionActions")
	#constraints
	#PrimaryKeyConstraint(EventID,GameID,name="pk_Events")
	'''
	EventTypes:
		StartGame
		EndGame
		StartRound - MiscData (round number)
		EndRound - MiscData (round number)
		Start_Turn - FactionName
		End_Turn - FactionName
		Pass_Turn - FactionName
		StartPhase - PhaseData (setup, strategy, action, status, agenda)
		EndPhase - PhaseData (setup, strategy, action, status, agenda)
		Speaker - FactionName
		Initiative - FactionName - MiscData (init number)
		End/StartState - ends/starts a state StateData(state "Active","Combat","Pause")
	'''

class Combats(Base):
	__tablename__="combats"
	#keys
	CombatID: Mapped[int] = mapped_column(primary_key=True)
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	Aggressor: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	Defender: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	Winner: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	Active: Mapped[bool] =mapped_column(default=1)	#combat status, only 1 active combat at a time
	#data
	StartTime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
	StopTime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())

	#relationships
	Game: Mapped["Games"]=relationship(back_populates="GameCombats")
	AggressorFaction: Mapped["Factions"]=relationship("Factions",foreign_keys=[Aggressor])
	DefenderFaction: Mapped["Factions"]=relationship("Factions",foreign_keys=[Defender])
	WinnerFaction: Mapped["Factions"]=relationship("Factions",foreign_keys=[Winner])
	

def clearAll():
	Base.metadata.drop_all(engine)
def createNew():
	Base.metadata.create_all(engine)
	
if __name__=="__main__":
	#createNew()
	print ("safe mode, doing nothing")
	

