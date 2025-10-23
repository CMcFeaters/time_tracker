from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats, Base, Turns
from sqlalchemy import select, or_, and_, delete, update, insert
from sqlalchemy.orm import sessionmaker
import datetime as dt
import sys

Session=sessionmaker(engine)
def addTurnTime():
	#find all turns
	#find eventIDS in turns (end event)
	#find the start event (event link from end event)
	#get the time delta between the two events
	with Session() as session:
		turns=session.scalars(select(Turns)).all()
		for turn in turns:
			endEvent=session.scalars(select(Events).where(Events.EventID==turn.EventID)).first()
			startEvent=session.scalars(select(Events).where(Events.EventID==endEvent.EventLink)).first()
			timeDelta=getTimeDelta(endEvent.EventTime,startEvent.EventTime)
			#print(f'Turn {turn.TurnID} Game: {turn.GameID} time: {timeDelta} start: {startEvent.EventTime} end: {endEvent.EventTime}')
			turn.TurnTime=timeDelta
			#not committing?
		session.commit()

def addTurnTimeStamp():
	'''
	uses the eventiD in turns to find teh timestamp of the closing event.
	sets the turntimestamp to the  closing event eventtime 
	'''
	with Session() as session:
		#function to return the eventTime object
		getEventTime=lambda eventID: session.scalars(select(Events).where(Events.EventID==eventID)).first().EventTime
		#get all the turns
		turns=session.scalars(select(Turns)).all()
		#for each turn, set the timestamp
		for turn in turns:
			turn.TurnTimeStamp=getEventTime(turn.EventID)
		session.commit()


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

	
def getTimeDelta(endTime,startTime):
	#given T1 and T2, returns the delta in seconds as an int
	return (endTime-startTime).total_seconds()

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
		
def convertStratergyData(GID=4):
	#this function will migrate the stategy data value in events (strategy card number)
	#and translate it to the strategycardnumber/name columns"
	strategyNameDict={None:None,1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial"}
	with Session() as session:
		#find all the entries where strategydata is not null and modify the dict
		x=session.scalars(select(Events).where(Events.GameID==GID, Events.StrategyData.isnot(None))).all()
		for entry in x:
			entry.StrategyCardNumber=int(entry.StrategyData)
			entry.StrategyCardName=strategyNameDict[int(entry.StrategyData)]
		#print(f'StragetyData: {x.StrategyData} is of type {type(x.StrategyData)}')
		session.commit()
	print(f'Done')

def convertMisctoStrategic(GID=4):
	#this function will migrate the MiscData from 1/2 when there is a strategic action into the StrategicActionData columndata value in events (strategy card number)
	#and translate it to the strategycardnumber/name columns"
	
	with Session() as session:
		#find all the entries where strategydata is not null and modify the dict
		x=session.scalars(select(Events).where(Events.GameID==GID, Events.StateData=="Strategic",((Events.EventType=="EndTurn") | (Events.EventType=="StartTurn")))).all()
		for entry in x:
			print(f'EntryID: {entry.EventID} MiscData: {entry.MiscData} ')
			entry.StrategicActionInfo=entry.MiscData
		#print(f'StragetyData: {x.StrategyData} is of type {type(x.StrategyData)}')
		session.commit()
	print(f'Done transferring miscdata to strategicactioninfo')

def endStateStrategic(GID=4):
	#finds all the strategic end states, adds the faction name, stratcard name and number
	with Session() as session:
		x=session.scalars(select(Events).where(
			Events.GameID==GID,
			((Events.EventType=="StartTurn") | (Events.EventType=="EndState")),
			Events.StateData=="Strategic")).all()
		sources={event.EventLink:session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==event.EventLink)).first() for event in x}
		for event in x:
			if sources[event.EventLink]:
				event.StrategyCardNumber=sources[event.EventLink].StrategyCardNumber
				event.StrategyCardName=sources[event.EventLink].StrategyCardName
		session.commit()
	print('done')

def scoreFix(GID=4):
	#updates score from miscdata containing the score, to scoretotla holding the score and the score column indicating+/-1
	with Session() as session:
		#eventDict={event.FactionName:None for event in 
		#[eventDict[event.FactionName]scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Score")).all()
		#factionEvents=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName.isnot(None))).all()
		pass

def convertMisctoTactic(GID=4):
	#updates the miscdata for endturns in the active state to tactic data.  should change to 0(nromal),1(pass),2(Combat)
	with Session() as session:
		x=session.scalars(select(Events).where(
			Events.GameID==GID,
			((Events.EventType=="EndTurn") | (Events.EventType=="PassTurn")),
			Events.StateData=="Active")).all()
		for event in x:
			event.TacticalActionInfo=event.MiscData
			event.EventType="EndTurn"
		session.commit()
	print("done")

def turnConvert():
	#converst all miscdata from turns to various other formats
	with Session() as session:
		#get strats
		ps={"Primary":1,"Secondary":2}
		tacticDict={"Tactical":0,"Action":0,"Pass":1,"Combat":2}
		strategyNameDict={None:None,"Leadership":1,"Diplomacy":2,"Politics":3,"Construction":4,"Trade":5,"Warfare":6,"Technology":7,"Imperial":8}
		strats=session.scalars(select(Turns).where(Turns.TurnType=="Strategic",((Turns.TurnInfo=="Primary") | (Turns.TurnInfo=="Secondary")))).all()
		stratTotal=session.scalars(select(Turns).where(Turns.TurnType=="Strategic",Turns.TurnInfo!="Primary", Turns.TurnInfo!="Secondary")).all()
		tactics=session.scalars(select(Turns).where(Turns.TurnType=="Tactical")).all()
		phases=session.scalars(select(Turns).where(Turns.TurnType=="Phase")).all()
		#combats=session.scalars(select(Turns).where(Turns.TurnType=="Combat")).all()
		actives=session.scalars(select(Turns).where(Turns.TurnType=="Active")).all()
		for strat in strats:
			strat.StrategicActionInfo=ps[strat.TurnInfo]
			strat.StrategyCardName=strat.MiscData
			strat.StrategyCardNumber=strategyNameDict[strat.MiscData]
		for strat in stratTotal:
			strat.StrategicActionInfo=0	#0 is when the strategy card ends
			strat.StrategyCardName=strat.MiscData
			strat.StrategyCardNumber=strategyNameDict[strat.MiscData]
		for tactic in tactics:
			tactic.TacticalInfo=tacticDict[tactic.TurnInfo]
		for phase in phases:
			phase.PhaseInfo=phase.MiscData
		session.commit()

def tacticalConvert():
	#convverst string tacticalinfo to integer tacticalactioninfo
	with Session() as session:
		tactics=session.scalars(select(Turns).where(Turns.TacticalInfo.isnot(None))).all()
		for tactic in tactics:
			tactic.TacticalActionInfo=int(tactic.TacticalInfo)
		session.commit()

def removePassTurn():
	#converts all passturns to "EndTurn" and "1" tacticalactioninfo
	with Session() as session:
		passes=session.scalars(select(Events).where(Events.EventType=="PassTurn")).all()
		for turn in passes:
			turn.EventType="EndTurn"
			turn.TacticalActionInfo=1
		session.commit()

if __name__=="__main__":
	if len(sys.argv)>1:
		safemode=sys.argv[1]
	else:
		safemode="fuck you"
	#just a little helper function
	if safemode=="1":
		addTurnTimeStamp()
	else:
		#roundMaker(1)
		print("safe mode enabled")