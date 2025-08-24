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

def addEndLink(GID=3):
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
					if (links[j].EventType=="EndPhase") & (links[i].PhaseData==links[j].PhaseData) & (links[i].Round==links[j].Round):
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
				
def turnFill(GID=2):
	#fills in the turns table
	#go through the events tables and get each:
	#STARTTurn-EndTurn
	#startturn-passturn (need to link ot an event ID)
		#need to differentiate between add a turntype
		
	#startphsae-endphase (can link by round number and phase id)
	#startaction
	turnType=['StartTurn','EndTurn','PassTurn','StartPhase','EndPhase']
	with Session() as session:
		events=session.scalars(select(Events).where(Events.GameID==GID,or_(Events.EventType=="StartTurn",Events.EventType=="EndTurn",Events.EventType=="PassTurn"))).all()
		
	
def getTimeDetla(t1,t2):
	#given T1 and T2, returns the delta in seconds as an int
	return (t1-t2).total_seconds()

if __name__=="__main__":
	if len(sys.argv)>1:
		safemode=sys.argv[1]
	else:
		safemode="fuck you"
	#just a little helper function
	if safemode=="1":
		addEndLink()
		
	else:
		#roundMaker(1)
		print("safe mode enabled")