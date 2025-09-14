from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats, Base, Turns
from sqlalchemy import select, or_, and_, delete, update, insert
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect
from time import sleep
import sys

Session=sessionmaker(engine)

def timeConvert():
	baseT=dt.datetime(1970,1,1)
	with Session() as session:
		times=session.scalars(select(Factions)).all()
		for t in times:
			#tSec=(t.TotalTime-baseT).total_seconds()
			tSec=t.TotalTime.total_seconds()
			print(f'{t.GameID} - {t.FactionName} - {tSec} - {int(tSec/3600)}:{int((tSec%3600)/60):02}:{int((tSec%3600)%60):02} --- {t.TotalTime}')
			t.tempTime=tSec
		session.commit()

def addEndLink(GID=1):
	#find all the start evnets and add an end link
	#for each start event, find the next end event
		#start events: startturn, startphase, startState, StartRound
		#we should change all passturns to endturns with a misc of 4
	with Session() as session:
		links=session.scalars(select(Events).where(
		Events.GameID==GID,or_(Events.EventType=="StartTurn",Events.EventType=="EndTurn",
		Events.EventType=="PassTurn",Events.EventType=="EndPhase",Events.EventType=="StartPhase",
		Events.EventType=="EndPhase",Events.EventType=="StartState",Events.EventType=="EndState",
		Events.EventType=="StartRound",Events.EventType=="EndRound")).order_by(Events.EventID.desc())).all()
		for i in range(0,len(links)):
			if (links[i].EventType=="StartTurn"):
				#find the appropriate EndTurn or PassTurn
				for j in range(i,-1,-1):
					if ((links[j].EventType=="EndTurn")|(links[j].EventType=="PassTurn")) & (links[i].FactionName==links[j].FactionName) & (links[i].Round==links[j].Round):
						#we have found the endphase event, 
						#print(f'StartTurn {links[i].EventID} - EndTurn {links[j].EventID}')
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[j].EventID).values(EventLink=links[i].EventID))
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[i].EventID).values(EventLink=links[j].EventID))
						break
				
			elif (links[i].EventType=="StartPhase"):
				#find the appropriate endphase
				for j in range(i,-1,-1):
					if (links[j].EventType=="EndPhase") & (links[i].PhaseData==links[j].PhaseData):
						#we have found the endphase event, 
						#print(f'StartPhase {links[i].EventID} - EndPhase {links[j].EventID}')
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[j].EventID).values(EventLink=links[i].EventID))
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[i].EventID).values(EventLink=links[j].EventID))
						break
						
			elif (links[i].EventType=="StartState"):
				#find the appropriate end state
				for j in range(i,-1,-1):
					if (links[j].EventType=="EndState") & (links[i].FactionName==links[j].FactionName):
						#we have found the endphase event, 
						#print(f'StartState {links[i].EventID} - EndState {links[j].EventID}')
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[j].EventID).values(EventLink=links[i].EventID))
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[i].EventID).values(EventLink=links[j].EventID))
						break
						
			elif (links[i].EventType=="StartRound"):
				#find the appropriate endRound
				for j in range(i,-1,-1):
					if ((links[j].EventType=="EndTurn")|(links[j].EventType=="PassTurn")) & (links[i].FactionName==links[j].FactionName) & (links[i].Round==links[j].Round):
						#we have found the endphase event, 
						#print(f'StartTurn {links[i].EventID} - EndTurn {links[j].EventID}')
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[j].EventID).values(EventLink=links[i].EventID))
						session.execute(update(Events).where(Events.GameID==GID,Events.EventID==links[i].EventID).values(EventLink=links[j].EventID))
						break
						
		session.commit()
				
def turnFill(GID=3):
	#fills in the turns table
	#go through the events tables and get each:
	#STARTTurn-EndTurn
	#startturn-passturn (need to link ot an event ID)
		#need to differentiate between add a turntype
		
	#startphsae-endphase (can link by round number and phase id)
	#startaction
	turnType=['StartTurn','EndTurn','PassTurn','StartPhase','EndPhase']	#a list with the various types of turn
	
	#a dict that is used to translate the event MISC data to a turn type
	endSwitcher={0:"Tactical",1:"Strategy",2:"Strategy",3:"Tactical",4:"Tactical",None:"Tactical"} 
	
	tacticalMisc={0:"Tactical",1:"Primary",2:"Secondary",3:"Combat",4:"Tactical",None:"Tactical"} 
	nones={0:None,1:None,2:None,3:None,4:None,None:None}
	#dict for the misc data
	miscSwitcher={None:None,1:"Primary",2:"Secondary"}
	#a dict that is used to convert the strat data from misc t0 a strat selected
	stratSwitcher={1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial",None:None}
	
	tactDict={"Tactical":tacticalMisc,"Strategy":stratSwitcher}	#look up iin the tact misc if it's a tactical and stratswitcher if it's strategic
	miscDict={"Tactical":nones,"Strategy":miscSwitcher}	#lookup in the miscsiwtcher if strat or not at all if tactic
	#tInfoSwitchter={None:None,
	with Session() as session:
		#get all of the relevant events for turn data
		events=session.scalars(select(Events).where(
			Events.GameID==GID,
			or_(
				Events.EventType=="StartTurn",
				Events.EventType=="StartPhase",
				Events.EventType=="StartState", 
				Events.EventType=="StartRound")
				).order_by(Events.EventID)).all()
		#for every event that has an eventlink (eventlink is a link to the finished event)
		for event in (x for x in events if x.EventLink is not None):
			#closeevent is the closing event to a starting event
			closeEvent=session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==event.EventLink)).first()
			#calculate the timedelta
			td=getTimeDelta(closeEvent.EventTime,event.EventTime)
			#look through the various event types 
			tInfo=None
			tMisc=None
			if (closeEvent.EventType=="EndPhase"):
				#if it's an event phase, the turntype is just the turn that ended
				ttype="Phase"
				tInfo=closeEvent.PhaseData
			elif (closeEvent.EventType=="PassTurn"):
				ttype="Tactical"
				tInfo="Pass"
			elif (closeEvent.EventType=="EndTurn"):
				#if it's an end turn, determine what type it is with MISC data
				ttype=endSwitcher[closeEvent.MiscData]
				#if it's a primary, we want the strategy
				#truninfo:
					#if it's a strategy, we need to identify the related strategic action 
					#if it's a tactical, identify if it's normal, combat
				#if it's a 
				#print(f'ttype: {ttype}')
				tInfo=tactDict[ttype][closeEvent.MiscData]	#double dict looup for the strategy card or the combat/tactical
				tMisc=miscDict[ttype][closeEvent.MiscData]	#nothing for tactical, prime/sec for strategy
			elif (closeEvent.EventType=="EndState"):
				#if we're ending a strategic state, we want to capture that state
				ttype=event.StateData
				tInfo=stratSwitcher[event.MiscData]	#if we are starting a state and it's a strategic state, misc data contains the strategy identifier
					
			elif (closeEvent.EventType=="EndRound"):
				ttype="Round"
			else:
				ttype=None
			session.add(Turns(
				GameID=GID,
				FactionName=event.FactionName,
				TurnTime=td,
				Round=event.Round,
				TurnType=ttype,
				TurnInfo=tInfo,
				MiscData=tMisc,
				TurnNumber=None,
				TurnNumberRound=None,
				EventID=closeEvent.EventID
				))	
		session.commit()

	
def getTimeDelta(t1,t2):
	#given T1 and T2, returns the delta in seconds as an int
	return (t1-t2).total_seconds()

def addStrategyData(GID=3):
	#adds the informaitno to the strategy data column in events
	#find all startstates, strategydata=lookup in dict miscdata
		#linked end state=startstate miscdata
		#all start/end turns in between =startstate miscdata
	#stratSwitcher={1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial",None:None}
	with Session() as session:
		
		startEvents=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState",Events.StateData=="Strategic")).all()
		endEvents=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="EndState",Events.StateData=="Strategic")).all()
		pairs=[(start,end) for start in startEvents for end in endEvents if start.EventID==end.EventLink]	#pair up the start and end states
		for pair in pairs:
			pair[0].StrategyData=pair[0].MiscData
			pair[1].StrategyData=pair[0].MiscData
			turns=session.scalars(select(Events).where(Events.GameID==GID,((Events.EventType=='StartTurn') | (Events.EventType=='EndTurn')),Events.EventID<pair[1].EventID,Events.EventID>pair[0].EventID)).all()
			for turn in turns:
				turn.StrategyData=pair[0].MiscData
		session.commit()
		#[print(f'{pair[0].EventID} - {pair[1].EventID}') for pair in pairs]
		

if __name__=="__main__":
	if len(sys.argv)>1:
		safemode=sys.argv[1]
	else:
		safemode="fuck you"
	#just a little helper function
	if safemode=="1":
		pass
		
		
	else:
		#roundMaker(1)
		print("safe mode enabled")