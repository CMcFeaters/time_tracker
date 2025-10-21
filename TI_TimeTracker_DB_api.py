
import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, create_engine, DateTime
from sqlalchemy.orm import declarative_base, relationship, mapped_column, Mapped
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql import func
from dotenv import dotenv_values
#define the MARIADB engine

config=dotenv_values(".env")	#laod the envinronment variabls
engine=create_engine("mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db']),pool_size=20,max_overflow=15)	#create the engine for connection
Base=declarative_base()

class Games(Base):
	__tablename__="games"
	#keys
	GameID: Mapped[int]=mapped_column(primary_key=True)
	#data
	GamePhase: Mapped[str]=mapped_column(String(30), default="Setup") #track teh current phase of the game
	GameState: Mapped[str]=mapped_column(String(30), default="Active")	#tracks teh current state (Pause, Active, Strategic)
	GameRound: Mapped[int]=mapped_column(default=0)	#tracks the game round
	GameDate: Mapped[datetime.date]	#date the game was setup
	GameWinner: Mapped[Optional[str]]=mapped_column(String(30))	#tracks winner of the game
	Active: Mapped[bool] =mapped_column(default=0)	#if active game: 1
	GameStrategyName: Mapped[Optional[str]]=mapped_column(String(30))	#when a strategy phase is active, identifies the current strat card name played
	GameStrategyNumber: Mapped[Optional[str]]=mapped_column(String(30))	#when a strategy phase is active, identifies the current strat card number played
	#relationship
	GameFactions: Mapped[List["Factions"]]=relationship('Factions',back_populates="GamePlayed")
	GameEvents: Mapped[List["Events"]]=relationship('Events',back_populates="Game")	
	#you need to remove this backlink to finish removing combat
	GameCombats: Mapped[List["Combats"]]=relationship('Combats',back_populates="Game")	#backlink to combats table
	GameTurns: Mapped[List["Turns"]]=relationship('Turns',back_populates="Game")	#backlink to combats table

	
class Users(Base):
	__tablename__="users"
	#keys
	UserID: Mapped[int]=mapped_column(primary_key=True)
	#data
	UserName: Mapped[str]=mapped_column(String(30), unique=True)
	#relationships
	FactionsPlayed: Mapped[List["Factions"]]=relationship('Factions',back_populates="User")
	

class Factions(Base):
	__tablename__="factions"
	#keys
	FactionName: Mapped[str]=mapped_column(String(50))
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	UserID: Mapped[int] = mapped_column(ForeignKey("users.UserID"))
	#data
	Active: Mapped[bool] =mapped_column(default=0)	#1 if currently active faction in active/tactic state, 0 if not
	ActiveStrategy: Mapped[bool] =mapped_column(default=0)	#1 if currently acting in strategy state, 0 if not
	TableOrder: Mapped[int] =mapped_column(default=0)
	Speaker: Mapped[bool] =mapped_column(default=0)
	Initiative: Mapped[int] =mapped_column(default=0)
	TotalTime: Mapped[Optional[int]]=mapped_column(default=0)
	Pass: Mapped[bool]=mapped_column(default=0)
	Score: Mapped[int]=mapped_column(default=0)
	UserName: Mapped[str]=mapped_column(String(30))
	Strategy1: Mapped[Optional[int]]=mapped_column(default=0)	#the number of the first strategy card
	Strategy2: Mapped[Optional[int]]=mapped_column(default=0)	#the number of the second strategy card
	StrategyStatus1: Mapped[Optional[int]]=mapped_column(default=0)	#the status of the first strategy card: 1: not used, 0:used
	StrategyStatus2: Mapped[Optional[int]]=mapped_column(default=0) #the status of the first strategy card: 1: not used, 0:used, -1: N/A
	StrategyName1: Mapped[Optional[str]]=mapped_column(String(30))
	StrategyName2: Mapped[Optional[str]]=mapped_column(String(30))

	
	#relationships
	GamePlayed: Mapped["Games"]=relationship('Games',back_populates="GameFactions")
	User: Mapped["Users"]=relationship('Users',back_populates="FactionsPlayed")
	FactionActions: Mapped[List["Events"]]=relationship('Events',back_populates="Faction")#is this right?
	FactionTurns: Mapped["Turns"]=relationship('Turns',back_populates="Faction")#is this right?
	#constraints
	PrimaryKeyConstraint(FactionName,GameID,name="pk_factions")#the primary key is made up of Factinoname and GameID so a unique entry in the table is this combination
	

class Events(Base):
	__tablename__="events"
	#keys
	EventID: Mapped[int] = mapped_column(primary_key=True)
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	FactionName: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))
	#data
	EventTime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
	EventType: Mapped[str]=mapped_column(String(30))
	PhaseData: Mapped[Optional[str]]=mapped_column(String(30))
	StateData: Mapped[Optional[str]]=mapped_column(String(30))
	Round: Mapped[Optional[int]]	#the round the event occured in
	EventLink: Mapped[Optional[int]]	#This is used ot link to start events and end events
	StrategyCardNumber: Mapped[Optional[str]]=mapped_column(String(30))	#captures the strategy card number for strategic action related cards
	StrategyCardName: Mapped[Optional[str]]=mapped_column(String(30))	#captures the strategy card name for strategic actions
	TacticalActionInfo: Mapped[Optional[int]]	#captures the strategic action type: normal (0), combat(1), pass(2)
	StrategicActionInfo: Mapped[Optional[int]]	#captures teh primary/secondary of a strategic action
	ScoreTotal: Mapped[Optional[int]]	#when a score event occurs, the total score
	Score: Mapped[Optional[int]]	#when a score occurs, the direction (+/-1)
	#relationships
	Game: Mapped["Games"]=relationship('Games',back_populates="GameEvents")
	Faction: Mapped["Factions"]=relationship('Factions',back_populates="FactionActions")
	EventTurns: Mapped["Turns"]=relationship('Turns',back_populates="Events")#is this right?
	
	
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
	
class Turns(Base):
	__tablename__="turns"

	#keys
	TurnID: Mapped[int] = mapped_column(primary_key=True)
	GameID: Mapped[int] = mapped_column(ForeignKey("games.GameID"))
	FactionName: Mapped[Optional[str]]=mapped_column(ForeignKey("factions.FactionName"))	#the ID of the faction, if applicable
	EventID: Mapped[Optional[int]]=mapped_column(ForeignKey("events.EventID"))	#the event ID of the closing event
	#data
	TurnTime: Mapped[Optional[int]]	#How long was the turn
	Round: Mapped[Optional[int]]	#the round the event occured in
	TurnType: Mapped[Optional[str]]=mapped_column(String(30))	#log the turn type - Tactical,Strategic, round,phase,game,state
	StrategyCardName: Mapped[Optional[str]]=mapped_column(String(30))	#if it's a strategic turn type, cpatures the strategic card name
	StrategyCardNumber: Mapped[Optional[int]]	#if it's a strategic turn type, captures the stategic card number
	TacticalActionInfo: Mapped[Optional[int]]	#if it's a tactical action turn, captures if it's normal (0), combat(1), or a pass(2)
	PhaseInfo: Mapped[Optional[str]]=mapped_column(String(30))	#if it's a phase turn, captures the phase name
	StrategicActionInfo: Mapped[Optional[int]] #if a strategic Action, captures if its a primary (1) or secndary (2)

	#relationships
	Game: Mapped["Games"]=relationship("Games",back_populates="GameTurns")
	Faction: Mapped["Factions"]=relationship("Factions",back_populates="FactionTurns")
	Events: Mapped["Factions"]=relationship("Events",back_populates="EventTurns",)

	#turnid - primary key
	#gameid - game indicator
	#eventID - The id of the closing event
	#facitoname - link to faction making the turn, if applicable
	#turnNumber - what number was this
	#turnNumberRound - what number was this
	#turn time - how long (in seconds) did this turn take
	#Round - what round did this occur during
	#turntype - what kind of turn was it (phase, strategic, tactical, status)
	#turninfo - what other info do we need to know?  (phase - status/strategy/tactic/agenda, strategic - what strategy card was it, tactical - normal or combat, status - active/stratgic/pause)
	#misc data - any other data we need (strategy - primary/secondary,state - what strategy cards was it)
	

	

#you need to remove this table from the DB to finish removing combats
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
	

