
import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, mapped_column, Mapped
from sqlalchemy.schema import PrimaryKeyConstraint
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
	GamePhase: Mapped[str]=mapped_column(String(30))
	GameRound: Mapped[int]
	GameDate: Mapped[datetime.date]
	#relationship
	GameFactions: Mapped[List["Factions"]]=relationship(back_populates="GamePlayed")
	GameEvents: Mapped[List["Events"]]=relationship(back_populates="GameID")	
	
class Users(Base):
	__tablename__="users"
	#keys
	UserID: Mapped[int]=mapped_column(primary_key=True)
	#data
	UserName: Mapped[str]=mapped_column(String(30))
	#relationships
	FactionsPlayed: Mapped[List["Factions"]]=relationship(back_populates="FactionName")
	

class Factions(Base):
	__tablename__="factions"
	#keys
	FactionName: Mapped[str]=mapped_column(String(50))
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	UserID: Mapped[int] = mapped_column(ForeignKey("users.UserID"))
	#data
	Active: Mapped[bool]
	TableOrder: Mapped[int]
	Speaker: Mapped[bool]
	Initiative: Mapped[int]
	TotalTime: Mapped[datetime.timedelta] 
	#relationships
	GamePlayed: Mapped["Games"]=relationship(back_populates="GameFactions")
	User: Mapped["Users"]=relationship(back_populates="FactionsPlayed")
	FactionActions: Mapped[List["Events"]]=relationship(back_populates="Faction")#is this right?
	#constraints
	PrimaryKeyConstraint(FactionName,GameID,name="pk_factions")

class Events(Base):
	__tablename__="events"
	#keys
	EventTime: Mapped[datetime.datetime] = mapped_column(insert_default=datetime.datetime.now())
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	FactionName: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	#data
	EventType: Mapped[str]=mapped_column(String(30))
	MiscData: Mapped[Optional[int]]
	#relationships
	Game: Mapped["Games"]=relationship(back_populates="GameEvents")
	Faction: Mapped["Factions"]=relationship(back_populates="FactionActions")
	#constraints
	PrimaryKeyConstraint(EventTime,GameID,name="pk_Events")
	'''
	EventTypes:
		StartGame
		EndGame
		StartRound - MiscData (round number)
		EndRound - MiscData (round number)
		Start_Turn - FactionName
		End_Turn - FactionName
		Pass_Turn - FactionName
		StartPhase - MiscData (strategy, action, status, agenda)
		EndPhase - MiscData (strategy, action, status, agenda)
		Speaker - FactionName
	'''

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
	

