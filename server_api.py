'''
	"backend" interface for teh server.  Includes all the functions called by the server when accessing the system
'''
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats, Base, Turns
from sqlalchemy import select, or_, and_, delete, update, insert
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect
from time import sleep
from collections import defaultdict
import sys

#modify when we create games
gdate=dt.date.today().strftime("%Y%m%d")

#update to reflect new game
strategyNameDict={1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial",9:"None"}
Session=sessionmaker(engine)


#####################	Search Functions 	#################################
def getSpeakerOrder(GID,active=False,names=False):
	'''
		returns an array of factions in table order starting with the identified factionname
	'''
	#this will sort by speaker for display
	
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		tFaction=[None]*len(factions)
		if active:	#speaker order starting with active
			bFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first()
		else:	#speaker order starting with speaker
			bFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Speaker==1)).first()
		if names:
			for faction in factions:
				tFaction[(faction.TableOrder-bFact.TableOrder)%len(factions)]=faction.FactionName
		else:
			for faction in factions:
				tFaction[(faction.TableOrder-bFact.TableOrder)%len(factions)]=faction
	return tFaction

def getSpeakerOrderByName(GID,factionName,names=False):
	'''
		returns an array of factions in table order starting with the identified factionname
	'''
	#this will sort by speaker for display
	
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		tFaction=[None]*len(factions)
		bFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==factionName)).first()
		if names:
			for faction in factions:
				tFaction[(faction.TableOrder-bFact.TableOrder)%len(factions)]=faction.FactionName
		else:
			for faction in factions:
				tFaction[(faction.TableOrder-bFact.TableOrder)%len(factions)]=faction
	return tFaction		

def activateGame(GID):
	'''
		given a GID, activates that game and commits
	'''
	with Session() as session:
		#print(f'activating game: {GID} type: {type(GID)}')
		session.scalars(select(Games).where(Games.GameID==GID)).first().Active=1
		session.commit()
	

def findNextSpeakerOrderByName(GID,factionName):
	'''
		returns the next faction name object using table order starting with the identified factionname
	'''
	#this will sort by speaker for display
	
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		tFaction=[None]*len(factions)
		bFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==factionName)).first()	#the current faction
		for faction in factions:
			tFaction[(faction.TableOrder-bFact.TableOrder)%len(factions)]=faction.FactionName
		nextFaction=tFaction[(tFaction.index(bFact.FactionName)+1)%len(tFaction)]
	return nextFaction		

def findNext(GID,fwd_bwd=1,passed=0):
	#returns the faction object of the next faction
	#GID - gameid
	#Fwd_bwd - 1 if the next next, -1 if the previous faction
	with Session() as session:
		#activeFactions contains the list of factions that haven't passed
		activeFactions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
		#print([faction.FactionName for faction in activeFactions])

		#there are some remaining unpassed factions
		#get a list of the current active intiatives, lined up in initiative order
			#if we're undoing, this includes whoever passed last
		activeInitiatives=session.scalars(select(Factions.Initiative).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
		#get teh current faction, this is who's turn it is right now, prior to updating the turn
			#next wants to find next, undo wants to find last
		currentFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first()
		#use current faction to find the next faction
		#iis the current faction still playing or passed?
		if activeInitiatives.count(currentFaction.Initiative)>0:
			#current factoin is still playing, they are in active init, increment intiatives and move forward (using mod)
			#in "undo" we are adding the faction back into the player pool so we will always be here
			nextIndex=(activeInitiatives.index(currentFaction.Initiative)+fwd_bwd)%len(activeInitiatives)
		else:
			#current faction has passed, we need to find the next faction in the list of passed factions 
			#bisect will find the spot to the left of where our initiative "would be" in the array of activite initiatives
			#if the current faction has passed it won't be in our active initiatives list and maintain sorted order
			nextIndex=bisect.bisect_left(activeInitiatives,currentFaction.Initiative)%len(activeInitiatives)	#we use %len in the event that it was the last person that passed so we can loop back to the start
		
		nextFaction=activeFactions[nextIndex]#get teh name to return
		#did this faction just pass?
		if ((nextFaction.FactionName==currentFaction.FactionName) & (passed==1)):
			#if so, it's the last faction and we need to return nothing.
			nextFaction=None
	return nextFaction

def findAndSetNext(GID,fwd_bwd=1):
	'''
	give the current active faction, determines the next active faction and returns the faction name.  if all factions have passed, return "none"
	
	updates the active factions 
	GID = game ID
	fwd_bwd = a value to determine if we are finding the next or previous faction +1 = next faction, -1 = previous faction
	'''
	with Session() as session:
		#activeFactions contains the list of factions that haven't passed
		activeFactions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
		#print([faction.FactionName for faction in activeFactions])
		if len(activeFactions)==0:	
			#if no one is active, clear the active faction and return "none"
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first().Active=False
			session.commit()	
			print(f'No active factions')
			return "none"
		else:
			#there are some remaining unpassed factions
			#get a list of the current active intiatives, lined up in initiative order
				#if we're undoing, this includes whoever passed last
			activeInitiatives=session.scalars(select(Factions.Initiative).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
			#get teh current faction, this is who's turn it is right now, prior to updating the turn
				#next wants to find next, undo wants to find last
			currentFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first()
			#use current faction to find the next faction
			#iis the current faction still playing or passed?
			if activeInitiatives.count(currentFaction.Initiative)>0:
				#current factoin is still playing, they are in active init, increment intiatives and move forward (using mod)
				#in "undo" we are adding the faction back into the player pool so we will always be here
				nextIndex=(activeInitiatives.index(currentFaction.Initiative)+fwd_bwd)%len(activeInitiatives)
			else:
				#current faction has passed, we need to find the next faction in the list of passed factions 
				#bisect will find the spot to the left of where our initiative "would be" in the array of activite initiatives
				#if the current faction has passed it won't be in our active initiatives list and maintain sorted order
				nextIndex=bisect.bisect_left(activeInitiatives,currentFaction.Initiative)%len(activeInitiatives)	#we use %len in the event that it was the last person that passed so we can loop back to the start
			
			#identify the factions whos turn it should be
			nextFaction=activeFactions[nextIndex].FactionName #get teh name to return
			#print(f'Next faction: {nextFaction}')
			#undo the current active faction
			currentFaction.Active=False
			#assign the identified faction as active
			activeFactions[nextIndex].Active=True
			session.commit()
			return nextFaction
			
def getPauseTime(GID,startEventID,stopEventID,session):
	'''
	finds the length of a pause
	finds all pauses with this faction
	finds all the pauses that occured since turnStart
	finds all the associated un-pauses
	calculates the time
	returns total_seconds() of the time delta
	'''
	pauseTime=dt.timedelta(0)
	
	#find all pauses since this turn start
	#find all the pause and unpause events that occured between the start and stop event IDs
	#print(f'Debug:  Starting Pause')
	pauseTime=0
	#find all the start pause events
	#print(f'Debug:  finding pauses between {startEventID} and {stopEventID}')
	pauses=session.scalars(select(Events).where(
		Events.GameID==GID,
		Events.EventType=="StartState",
		Events.StateData=="Pause",
		Events.EventID>startEventID,
		Events.EventID<stopEventID
		).order_by(Events.EventID.desc())).all()
	#find the total time spent paused in these events
	#print(f'Debug:  CreaTING pAUSE Array')
	pauseArray=[(session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==pause.EventLink)).first().EventTime-pause.EventTime).total_seconds() 
		for pause in pauses]
	#add up the pauses
	#print(f'Debug:  adding up pause time')
	for pause in pauseArray:
		print(f'Pause {pause}')
		pauseTime+=pause
	
	#print(f'Debug:  Total Time: {pauseTime} - {type(pauseTime)}')
	return pauseTime
		
def getFactions(GID):
	'''
		returns a list of the factions
	'''
	with Session() as session:
		factions= session.scalars(select(Factions).where(Factions.GameID==GID)).all()
	return factions

#####################	Modify Functions 	#################################

def deleteOldGame(GID):
	'''
	given a game ID, deletes all entries associated with that gameID
	deletes from:
		Games Table
		Factions Table
		Events Table
		Combats Table
	'''
	with Session() as session:
		session.query(Combats).filter(Combats.GameID==GID).delete()
		session.query(Events).filter(Events.GameID==GID).delete()
		session.query(Factions).filter(Factions.GameID==GID).delete()
		session.query(Games).filter(Games.GameID==GID).delete()
		session.commit()

def getTurnTime(GID,startEvent,endEvent,session):
	#returns the factions new total time
	#GID - Game ID
	#endEvent is the ending Event
	#startEvent is the starting event
	#calcuates the total time of (faction) between (faction's) most recent
	#start turn and end turn
	#will subtract out any pause time using getPauseTime
	#with Session() as session:
		#get teh start and stop time marks, then subtract them to get the full time of the turn
		
		#factions most recent start
		#turnStart=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	
		#find the stop associated with this start
		#factions most recent stop
		#turnStop=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==turnStart.EventID)).first()
		#calculate the time between the two events
	#print(f'Debug:  Start: {startEvent.EventID} Stop: {endEvent.EventID}')
	#print(f'Debug:  StartTime: {startEvent.EventTime} StoptTime: {endEvent.EventTime}')
	
	turnTime=(endEvent.EventTime-startEvent.EventTime).total_seconds()	#we are now doing total seconds and storing as an int, rather than a datetime
	#print(f'Debug:  	turntime: {turnTime}')
		#subtract out any pauses/combats
	turnTime-=getPauseTime(GID,startEvent.EventID,endEvent.EventID,session)
		#find the faction we're doing the time modification for
		#actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		
		#determine if this is a normal time add or if we're undoing a turn
		#totalTime=actFact.TotalTime+(fwd_bwd*turnTime)
	#print(f'Debug:  	turntime-Pause: {turnTime}')
	return turnTime


def undoEndStrat(GID):
	#this is the functino called when undoing form the strategic action screen
	#it can undo strategic state-active state (doesn't impact an end turn), keeps the same turn and drops you to the tactic screen
	#it can undo a strategic state - strategic state, moving from a secondary to a secondary
	with Session() as session:
		#find the previous end event
		prevEnd=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="EndTurn").order_by(Events.EventTime.desc())).first()
		#get the basegame
		baseGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#determine if we're going back to a tactical action
		if (prevEnd.TacticalActionInfo is not None):
			#undo the state change events
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState").order_by(Events.EventTime.desc())).first().EventType="Correct-StartState"
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="EndState").order_by(Events.EventTime.desc())).first().EventType="Correct-EndState"
			#find the active faction
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
			#Reactivate the active faction's strategy card
			if activeFaction.Strategy1==int(baseGame.GameStrategyNumber):
				activeFaction.StrategyStatus1=1
			elif activeFaction.Strategy2==int(baseGame.GamesStrategyNumber):
				activeFaction.StrategyStatus2=1
			#update the game state
			baseGame.GameState="Active"
			#clear the game strats
			baseGame.GameStrategyNumber=None
			baseGame.GameStrategyName=None
			#clear the current activestrat
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.ActiveStrategy==1)).first().ActiveStrategy=0
			print(f'undid a strat-tact')
		#determine if we are going back to a previous strategic action
		elif (prevEnd.StrategicActionInfo is not None):
			#find the current start
			currStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			#find the currently active faction
			currFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.ActiveStrategy==1)).first()
			#find previously active Faction
			prevFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first()
			#find the previous start associated with the previous end
			prevStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==prevEnd.EventID)).first()
			#subrtract the previous turn time from the faction's total time
			prevFact.TotalTime-=getTurnTime(GID,prevStart, prevEnd,session)
			#update current faction active status
			#correct current start
			currStart.EventType="Correct-StartTurn"
			#correct prevEnd
			prevEnd.EventType="Correct-EndTurn"
			prevEnd.EventLink=None
			#clear teh current active strategy
			currFact.ActiveStrategy=0
			#update the previous active strategy
			prevFact.ActiveStrategy=1
			print(f'undid a strat-strat')
		else:
			print(f'undid nothing apparently')
		#create correct event
		newCorrect=Events(
			GameID=GID,
			EventType="CorrectTurn",
			PhaseData=baseGame.GamePhase,
			StateData=baseGame.GameState,
			Round=baseGame.GameRound
		)
		session.add(newCorrect)
		session.commit()

def undoEndTurn(GID,faction):
	#This is the function called when undoing from the tactical action screen
	'''
	undos ending a faction's turn, if it's undoing a pass(1), updates passing
	reverts to the previous faction's turn
	prevent going beyond start of round
	X-updates total time
	remove the new start turn event
	removes the end turn event
	X-adds a correction event
	X-updates pass status
	X-ID previous faction
	X-call startTurn
	
	'''
	with Session() as session:
		
		#find the base game
		baseGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#find the previous endturn 
		prevEnd=session.scalars(
			select(Events).where(
				Events.GameID==GID,
				Events.EventType=="EndTurn"
				).order_by(
					Events.EventID.desc())
					).first()
		#check to see if you're trying to undo the absolute first turn
		#Note: if you're udnoing initiatives, this is where you'd undo the first initiative selection
		if prevEnd is None:
			#print(f'-Cant go beyond first round')
			return "None"
		#check to see if we're trying to go into the previous round
		#NOTE: If you want undo initiatives, this is where youd do it
		elif baseGame.GameRound>prevEnd.Round:
			#print(f'-previous round {prev_end.Round} less than current {curRound}')
			return "None"
		#chedk to see if we are doing a basic active-active undo
		if ((prevEnd.StateData=="Active")&(baseGame.GameState=="Active")):
			#correct the start of the current turn
			currStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			#find the previous start associated with the previous end
			prevStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==prevEnd.EventID)).first()
			#correct the previous faction time
			prevFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first()
			#subrtract the previous turn time from the faction's total time
			prevFact.TotalTime-=getTurnTime(GID,prevStart, prevEnd,session)
			#update the active faction
			print(f'Were doing an undo end')
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().Active=0
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().Active=1
			#check to see if it was a pass
			if prevEnd.TacticalActionInfo==1:
				#update the pass status
				session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().Pass=0
			#correct prevEnd's event link
			prevEnd.EventLink=None
			#correct currStart event Type
			currStart.EventType="Corrected-StartTurn"
			#correct the previous faction end turn
			prevEnd.EventType="Corrected-EndTurn"
			#correct the event linked to the prevEnd
			prevStart.EventLink=None
			#correct the previous turn entry
			session.scalars(select(Turns).where(Turns.GameID==GID,Turns.EventID==prevEnd.EventID)).first().TurnType="Corrected-Tactical"
		#see if we're going from a active start to a strateigc end
		elif ((prevEnd.StateData=="Strategic") & (baseGame.GameState=="Active")):
			print(f'Debug: Undoing active to strat')
			#correct the start of the current turn
			currStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			print("1")
			#correct the previous faction time
			prevFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first()
			#find the previous start associated with the previous end
			prevStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==prevEnd.EventID)).first()
			#subrtract the previous turn time from the faction's total time
			print("Completed gatehring data")
			prevFact.TotalTime-=getTurnTime(GID,prevStart, prevEnd,session)
			print("Completed uupdating time")
			#clear the currently active player
			print(f'were doing an undoend turn')
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().Active=0	#this is correct, this person is no longer active
			#set the previous end turn faction to activestrategy=1, e.g., going next
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().ActiveStrategy=1	#this is who needs to be making the strategic action
			#find the previously active faction
			previousActiveFaction=findNext(GID,fwd_bwd=-1,passed=0)	#the previously active faction did not pass, the completed a strategic action
			#update the active status of the previousy active faction
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==previousActiveFaction.FactionName)).first().Active=1
			#update the gamestate
			baseGame.GameState="Strategic"
			#update the game strategy info
			baseGame.GameStrategyName=prevEnd.StrategyCardName
			baseGame.GameStrategyNumber=prevEnd.StrategyCardNumber
			#find the faction that executed this strategy card
			prevFaction=session.scalars(select(Factions).where(
				Factions.GameID==GID, 
				((Factions.Strategy1==prevEnd.StrategyCardNumber)|(Factions.Strategy2==prevEnd.StrategyCardNumber))
				)).first()
			#determine if it was the first or second strat played, then update that back to 1
			if prevFaction.Strategy1==prevEnd.StrategyCardNumber:
				prevFaction.StrategyStatus1=1
			elif prevFaction.Strategy2==prevEnd.StrategyCardNumber:
				prevFaction.StrategyStatus2=1
			#correct the previous turn entry
			session.scalars(select(Turns).where(Turns.GameID==GID,Turns.EventID==prevEnd.EventID)).first().TurnType="Corrected-Strategic"
			#find and correct the Active start state
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState").order_by(Events.EventTime.desc())).first().EventType="Corrected-StartState"
			#find the "strategic" end state
			stratEnd=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="EndState").order_by(Events.EventTime.desc())).first()
			#correct the strategic end state
			stratEnd.EventType="Corrected-EndState"
			stratEnd.EventLink=None
			#correct prevEnd's event link
			prevEnd.EventLink=None
			#correct the current start turn
			currStart.EventType="Corrected-StartTurn"
			#correct the previous faction end turn
			prevEnd.EventType="Corrected-EndTurn"
			#correct the event linked to the prevEnd
			prevStart.EventLink=None
			#correct the stratend turn entry
			session.scalars(select(Turns).where(Turns.GameID==GID,Turns.EventID==stratEnd.EventID)).first().TurnType="Corrected-Strategic"
		#any undo originating from the strategic action screen will call undoEndStrat
		#do major gamestate updates
		session.add(Events(GameID=GID,EventType="CorrectTurn", Round=baseGame.GameRound, StateData=baseGame.GameState, PhaseData=baseGame.GamePhase))	#create the event marking a turn correction ("CorrectTurn"
		session.commit()
	#update time here, now that we know the previous faction
	#print(f'-Updating the time for {prev_end.FactionName}')
	#update the current turn facionts start turn and the previous turn factions end/pass turn recent start/endturn events

def endTurn(GID,faction,tacticalActionInfo=0):
	'''
	
	ends a faction's turn, if it's a pass(1), updates passing
	start's the next faction's turn
	
	create the end/pass event
	update pass status
	ID next faction
	update total time
	call startTurn or, if all pass, end phase
	Assigns tacticalactionifo to default 0.  0:Normal,1:Pass,2:Combat
	'''
	#print(f'Engine Start: checked out: {engine.pool.checkedout()} checkedin {engine.pool.checkedin()}')
	#print(f'Engine: {engine.pool.status()}')
	with Session() as session:
		#find the related start event
		startTurn=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction, Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
		#create the end event
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		endEvent=Events(GameID=GID,
			EventType="EndTurn",
			TacticalActionInfo=tacticalActionInfo,
			FactionName=faction, 
			Round=gameBase.GameRound,
			EventLink=startTurn.EventID,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState)	#create the event
		session.add(endEvent)
		#make the changes so we can access that event ID
		session.flush()
		#if the faction is passing, update their status to passing
		if tacticalActionInfo==1:
			session.execute(update(Factions).where(Factions.FactionName==faction).values(Pass=1))
		#update the event link for our start faction
		startTurn.EventLink=endEvent.EventID
		
		#create the endturn turn entry
		turnEntry=Turns(
					GameID=GID,
					TurnTime=getTurnTime(GID,startTurn,endEvent,session),
					Round=gameBase.GameRound,
					FactionName=faction,
					TurnType="Tactical",
					TacticalActionInfo=tacticalActionInfo,
					EventID=endEvent.EventID
					)
		#add the turn entry
		session.add(turnEntry)
		#update the faction's time
		prevFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		#add the previous turn time from the faction's total time
		prevFact.TotalTime+=getTurnTime(GID,startTurn, endEvent,session)
		#clear the active status lf the previous faction
		#get the enxt faction
		if findNext(GID,passed=tacticalActionInfo) is not None:
			nextFaction=session.scalars(select(Factions).where(
				Factions.GameID==GID,
				Factions.FactionName==findNext(GID,passed=tacticalActionInfo).FactionName
			)).first()
		else:
			nextFaction=None
		prevFact.Active=0
		#check to see if this faction passed
		#nextfaction is pulling from the DB, which should have been commited?  Either way it's logging pass as false
		#if there is a next faction, activeate them, add the start event, commit the session
		if nextFaction is not None:
			print(f'debug: were setttging {nextFaction.FactionName} action to 1')
			#active next faction
			nextFaction.Active=1
			#create and add the start turn event
			newStartTurnEvent=Events(GameID=GID,
				EventType="StartTurn",
				FactionName=nextFaction.FactionName, 
				Round=gameBase.GameRound,
				PhaseData=gameBase.GamePhase,
				StateData=gameBase.GameState)
			session.add(newStartTurnEvent)
			#commit the session
			session.commit()
		#if tehre is no next faction, end the phase
		elif nextFaction is None:

			#print("Ending phase due to no players left")
			print("ending phase")
			endPhase(GID,False,session)
			print("phase ended")
		else:
			print(f'Welp, looks like we fucked up')
		

def closeStrat(GID):
	#this function will end the active strategy turn, 
	# set the strategystatusX value to 0 from teh calling faction,
	# set the gamestate to active, start the next factions turn
	# this function is called from the strategic action page when the last faction to act closes their turn
	#
	
	with Session() as session:
		#find the base game
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#find the current strat
		strat=(gameBase.GameStrategyNumber,gameBase.GameStrategyName)
		#find the faction that called the strat (they called the strat)
		actFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first()
		#find the faction that is currently closing their secondary strategic action
		stratFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.ActiveStrategy==1)).first()
		#this is missing a stratstart event, why are we doing a "stratEND"?instead just a turn and a normal stateEnd?
		#create the overall strategy turn
		print(f'Debug: GameBase Strategy - {gameBase.GameStrategyNumber} | {gameBase.GameStrategyName}')
		print(f'Debug: STRAT Strategy - {strat[0]} | {strat[1]}')
		print(f'Debug: Strategy1 - {actFaction.Strategy1} | {actFaction.StrategyStatus1}')
		print(f'Debug: Strategy2 - {actFaction.Strategy2} | {actFaction.StrategyStatus2}')
		#determine if the active faction use their first or second [4 player] strategy card and set to 0
		if int(strat[0])==actFaction.Strategy1:	#find teh appropriate strat and show it as closed
			actFaction.StrategyStatus1=0
		else:
			actFaction.StrategyStatus2=0
		#create an event to end the strategic action of activestrategy 
		#this finds teh most recent startturn event (e.g., whoevers turn just started)
		startTurnEvent=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartTurn",
			Events.FactionName==stratFaction.FactionName
			).order_by(Events.EventTime.desc())).first()
		#create an end turn event for a secondary
		endTurnEvent=Events(
			GameID=GID,
			EventType="EndTurn",
			StrategicActionInfo=2,
			FactionName=stratFaction.FactionName,
			Round=gameBase.GameRound,
			EventLink=startTurnEvent.EventID,
			StrategyCardName=gameBase.GameStrategyName,
			StrategyCardNumber=gameBase.GameStrategyNumber,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState,
			ScoreTotal=stratFaction.Score
		)	
		#add and flush
		session.add(endTurnEvent)
		session.flush()	#flush to get data
		
		#create the turn event as a secondary
		session.add(Turns(
			GameID=GID,
			TurnType="Strategic",
			StrategicActionInfo=2,
			StrategyCardName=gameBase.GameStrategyName,
			StrategyCardNumber=gameBase.GameStrategyNumber,
			FactionName=stratFaction.FactionName,
			Round=gameBase.GameRound,
			TurnTime=getTimeDelta(endTurnEvent.EventTime,startTurnEvent.EventTime),
			EventID=endTurnEvent.EventID))
		#update teh turn link
		startTurnEvent.EventLink=endTurnEvent.EventID	#update the linkage
		#add the previous turn time from the faction's total time
		stratFaction.TotalTime+=getTurnTime(GID,startTurnEvent, endTurnEvent,session)
		#update activestrategy status for current
		stratFaction.ActiveStrategy=0
		#begin previous state change
		
		#find the previous state start event
		previousStartStateEvent=session.scalars(select(Events).where(
				Events.GameID==GID,
				Events.EventType=="StartState",
				Events.StateData==gameBase.GameState
			).order_by(Events.EventID.desc())).first()

	#createthe new ednstate event 
		newEndStateEvent=Events(GameID=GID,
			EventType="EndState",
			FactionName=None,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState, 
			Round=gameBase.GameRound,
			EventLink=previousStartStateEvent.EventID)
	
	#flush to create the added event
		session.add(newEndStateEvent)
		session.flush()

	#link the previous event
		newEndStateEvent.EventLink=previousStartStateEvent.EventID
	
	#create the new turn for ending a strategic action
		session.add(
					Turns(
						GameID=GID,
						Round=gameBase.GameRound,
						TurnType="Strategic",
						EventID=newEndStateEvent.EventID,
						TurnTime=getTurnTime(GID,newEndStateEvent,previousStartStateEvent,session),
						StrategicActionInfo=0,
						StrategyCardName=gameBase.GameStrategyName,
						StrategyCardNumber=gameBase.GameStrategyNumber
					)
		)

		#update the basegame
		gameBase.GameStrategyName=None
		gameBase.GameStrategyNumber=None
		gameBase.GameState="Active"
		
		#begin starting the next factions turn
		nextActive=session.scalars(select(Factions).where(
			Factions.GameID==GID,
			Factions.FactionName==findNext(GID).FactionName
			)).first()

		#update active status
		nextActive.Active=1
		actFaction.Active=0
		#add the startturnevent
		session.add(
			Events(
				GameID=GID,
				FactionName=nextActive.FactionName,
				EventType="StartTurn",
				StateData=gameBase.GameState,
				PhaseData=gameBase.GamePhase,
				Round=gameBase.GameRound,
				ScoreTotal=nextActive.Score
			)
		)
		session.commit()

def stopGame(GID):
	'''
	deactivate teh current game
	
	'''
	with Session() as session:
		session.scalars(select(Games).where(Games.GameID==GID)).first().Active=0
		session.commit()
	

def deactivateGames():
	'''
	helper function that deactivates all games
	and returns None
	called from getActiveGame to handle more than 1 active game
	'''
	with Session() as session:
		games=session.scalars(select(Games).where(Games.Active==1)).all()
		for game in games:
			game.Active=0
		session.commit()
		print('multiple acgive games')
	return None

def getActiveGame():
	'''
	returns the game object of the currently active game
	if no games are active returns None
	if multiple games are active, sets those games to innactive (0) and returns None
	'''
	
	with Session() as session:
		activeGame=session.scalars(select(Games).where(Games.Active==1)).all()
		#dict that returns the following
		# if there is 1 activeGame, return that gameID
		# if there is 0 activeGames, return None
		# if there are more than 1 active games, clear them and return None
		returnDict={1:lambda:activeGame[0],0:lambda:None}
		#change this to return the gameobject, then deriveGameID
		return returnDict.get(len(activeGame),deactivateGames)()
				 

def getRawData():
	'''
	data capture fucntion, returns:
		the list of all games (objects)
		the list of all users (objects)
	'''
	with Session() as session:
		#get a list of games
		games=session.scalars(select(Games).order_by(Games.GameID)).all()
		#get a list of 
		users=session.scalars(select(Users).order_by(Users.UserName)).all()
	return({'games':games,'users':users})
def getGameData(GID=None):
	'''
	data capture function, returns:
		the list of factions (objects) in initiative order
		the active faction (object)
		the active user (object)
		the activegame (object)
		list of games (objects)
		list of users (objects)
	in a {factions:factions,activeFaction:activeFaction,activeUser:activeUser,game:activeGame,games:games,users:users} format
	for the current Game
	'''
	with Session() as session:
		#get list of factions
		factions=session.scalars(select(Factions).where(
			Factions.GameID==GID
		).order_by(Factions.Initiative)).all()
		#get active faction
		activeFaction=session.scalars(select(Factions).where(
			Factions.GameID==GID,
			Factions.Active==1
		)).first()
		#get active user only if there is an active faction
		activeUser={None:lambda:None}.get(activeFaction,lambda:session.scalars(select(Users).where(
		Users.UserID==activeFaction.UserID
		)).first())()
		#get active Game
		gameBase=session.scalars(select(Games).where(
			Games.Active==1
		)).first()

	return {"factions":factions,"activeFaction":activeFaction,"activeUser":activeUser,'game':gameBase}

def transitionStrat(GID,currentFactionName,nextFactionName):
	'''
	 this function will create:
	 an strategic endturn event for teh current faction
	 a turn entry for teh current faction
	 will update the faction.activestrategy to 0 for the active faction
	 create a start turn eent for the new strat player
	 update teh new player's srtategic action
	updated to create turn data for a strategic-primary/secondary-stratID turn
	'''
	with Session() as session:
		#this finds teh most recent startturn event (e.g., whoevers turn just started)
		startEvent=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartTurn",
			Events.FactionName==currentFactionName
			).order_by(Events.EventTime.desc())).first()
		#this is the basegame event used to extract and capture game info
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#grab a base faction to capture faction info
		currFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==currentFactionName )).first()
		#determine if we're ending teh primary or secondary 
		if session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().FactionName==currentFactionName:	#if the calling faction is the active faction, it's aprimary
			state=1	#primary strate
		else:	#else it's a secondary
			state=2	#secondary strat
		#create the endturn event
		newEnd=Events(
			GameID=GID,
			EventType="EndTurn",
			StrategicActionInfo=state,
			FactionName=currentFactionName,
			Round=gameBase.GameRound,
			EventLink=startEvent.EventID,
			StrategyCardName=gameBase.GameStrategyName,
			StrategyCardNumber=gameBase.GameStrategyNumber,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState,
			ScoreTotal=currFaction.Score
		)
			
		#add and flush
		session.add(newEnd)
		session.flush()	#flush to get data
		
		#create the turn event
		session.add(Turns(
			GameID=GID,
			TurnType="Strategic",
			StrategicActionInfo=state,
			StrategyCardName=gameBase.GameStrategyName,
			StrategyCardNumber=gameBase.GameStrategyNumber,
			FactionName=currentFactionName,
			Round=gameBase.GameRound,
			TurnTime=getTimeDelta(newEnd.EventTime,startEvent.EventTime),
			EventID=newEnd.EventID))
		startEvent.EventLink=newEnd.EventID	#update the linkage

		#add the previous turn time from the faction's total time
		currFaction.TotalTime+=getTurnTime(GID,startEvent, newEnd,session)
		#update activestrategy status for current
		currFaction.ActiveStrategy=0
		#Begin startig the next faction's turn
		#note strategicactioninfo is always 2, since this is always a secondary action.  THe start of the strategy turn is captured as a generic start turn and is indicated 
		newStartEvent=Events(
			GameID=GID,
			EventType="StartTurn",
			FactionName=nextFactionName,
			StrategicActionInfo=2,
			Round=gameBase.GameRound,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState,
			StrategyCardNumber=int(gameBase.GameStrategyNumber),
			StrategyCardName=strategyNameDict[int(gameBase.GameStrategyNumber)]
			)
		session.add(newStartEvent)
		#set the active strategy status to 1
		session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==nextFactionName)).first().ActiveStrategy=1
		session.commit()


def assignStrat(GID,stratDict):
	'''
		given a stratDict, assigns the strategy 1,2 to each faction
		sets the strat status appropriately
		calls the intiative fucntion
	'''
	with Session() as session:
		for key in stratDict:
			#get each faction
			faction=session.scalars(select(Factions).
			where(Factions.FactionName==key,Factions.GameID==GID)).first()
			#assign stategy cards
			faction.Strategy1=stratDict[key][0]
			faction.Strategy2=stratDict[key][1]
			#assign names
			faction.StrategyName1=strategyNameDict[stratDict[key][0]]
			faction.StrategyName2=strategyNameDict[stratDict[key][1]]
			#assign strategy status, 1,0,-1 : ready, used, N/A
			faction.StrategyStatus1=1
			if stratDict[key][1]<9:
				faction.StrategyStatus2=1
			else:
				faction.StrategyStatus2=-1
			#assign initiative
			faction.Initiative=min(stratDict[key][0],stratDict[key][1])
			#end the strategy phase, this commits
		endPhase(GID,False,session)
			
def updateInitiative(GID,initiative):
	'''
	takes in a dict of initiatives in order of {"faction name":"initiative"} and updates
	can do single or batch
	'''
	with Session() as session:		
		for key in initiative:
			session.scalars(select(Factions).
			where(Factions.FactionName==key,Factions.GameID==GID)).first().Initiative=initiative[key]
		session.commit()

def newSpeaker(GID,faction):
	'''
	removes current speaker and assigns the given faction the speaker priority
	'''
	
	with Session() as session:
		#event
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		session.add(Events(GameID=GID,EventType="Speaker",FactionName=faction, Round=gameBase.GameRound))
		#update state
		session.execute(update(Factions).where(Factions.GameID==GID).values(Speaker=False))
		session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==faction).values(Speaker=True))
		session.commit()
		
def adjustPoints(GID,faction,points):
	'''
	adjusts the points for a faction by "points".  Can be positive or negative, creates event and then updates the scores
	'''
	with Session() as session:
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		res=session.scalars(select(Factions).where(Factions.FactionName==faction,Factions.GameID==GID)).first()
		res.Score+=points
		session.flush()
		session.add(Events(GameID=GID,EventType="Score",FactionName=faction,Score=points,ScoreTotal= res.Score,Round=gameBase.GameRound()))
		session.commit()
			
def gameStop(GID,faction):
	'''
	ends the game by creating a stop game event
	'''

	with Session() as session:
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		session.scalars(select(Games).where(Games.GameID==GID)).first().GameWinner=faction
		session.add(Events(GameID=GID,EventType="GameStop", Round=gameBase.GameRound))
		endPhase(GID,True,session)
	
		
def startPhase(GID,session):
	'''
	takes in an active session
	adds the startphase events, and takes care of the details for starting each phase
	when starting action phase, activates the lowest initiative faction, 
	when starting the agenda phase, sets intiatives to 0
	when starting the strategy phase, increments the gound round and creates start/stop round eventrs
	when starting the status phase, clears initiatives and the pass status'
	updates game table
	then it commits the session
	'''
	phase_order={"Setup":"Strategy","Strategy":"Action","Action":"Status","Status":"Agenda","Agenda":"Strategy"}
	
	currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
	#if it's the setup phase, we need to add a gamestart event since the game is starting
	#if (currentGame.GamePhase=="Setup"):
	#		session.add(Events(GameID=GID,EventType="GameStart", Round=currentGame.GameRound))
	#create new phase and update
	newPhase=phase_order[currentGame.GamePhase]	#use the dict to bump us to the next phase, separate so it persists
	currentGame.GamePhase=newPhase
	#this dict is used to increment the round by 1 if we're adding a strategy start phase (we increment the start in phasechangedetails
	#but i want to do it this way to prevent an if statement
	strat_dict={"Strategy":1}
	#create a defaultdict that only adds 1 when it's a strategy phase
	roundAdder=defaultdict(lambda:0,strat_dict)
	#add the start phase event for the new phase, note we're incrementing round+1 if we're entering the strategy phase
	
	session.add(Events(
		GameID=GID,
		EventType="StartPhase",
		PhaseData=newPhase,
		StateData=currentGame.GameState,
		Round=currentGame.GameRound+roundAdder[newPhase]
		))	#create the event
	#determine which phase we are going to and perfomr the phase specific deatil actions
	if newPhase=="Action":
		#entering the action phase we need to automatically assign the active faction 
		#and start their turn
		#if we're entering the action phase, first initiative is the active faction
		activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).first()
		newEvent=Events(GameID=GID,
			EventType="StartTurn",
			FactionName=activeFaction.FactionName, 
			Round=currentGame.GameRound,
			PhaseData=currentGame.GamePhase,
			StateData=currentGame.GameState
		)
		session.add(newEvent)
		#active the active Faction
		activeFaction.Active=1

	elif newPhase=="Agenda":
		#clear all the initiatives
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		for row in factions:
			row.Initiative=0 #set all inits to 0

	elif newPhase=="Strategy":
		#end old round, start new round, increment gameround
		session.add(Events(GameID=GID,EventType="EndRound", Round=currentGame.GameRound))
		session.add(Events(GameID=GID,EventType="StartRound", Round=currentGame.GameRound+1))
		currentGame.GameRound+=1		

	elif newPhase=="Status":
	#clear all of the "pass" and active status
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		for row in factions:
			row.Pass=0 #set all pass status to 0
			row.Active=0	#set all to inactive

	session.commit()
	 
def changeState(GID,state,faction=None):
	'''
	updates the state of the current game. called when changing pause-active-strategic
	state is the new state
	'''
	with Session() as session:
		##
		#get the current state of the current game
		#we are updating to the passed in state: "Pause", "Active", "Strategic"
		##
		#get the current game, we'll use this to figure out the current state and update the game state
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()	
		
		#find the event that captures the previous state, this is the last "startstate" that matches the input "state"
		previousState=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState",Events.StateData==currentGame.GameState).order_by(Events.EventID.desc())).first()
		
		#prepare the new event. 
		newEvent=Events(GameID=GID,
			EventType="EndState",
			FactionName=faction,
			PhaseData=currentGame.GamePhase,
			StateData=currentGame.GameState, 
			Round=currentGame.GameRound,
			EventLink=previousState.EventID)
		
		#add the event, and then flush so we can use the eventID in the rest of the process
		session.add(newEvent)	
		session.flush()	
		
		#add the event that indicates the state change
		session.add(Events(
			GameID=GID,
			EventType="StartState",
			PhaseData=currentGame.GamePhase,
			StateData=state, 
			Round=currentGame.GameRound)) 	#add an event to start the current phase
		
		#if we are ending a pause add a Turn for pause
		if currentGame.GameState=="Pause":	#if it's a pause, we want to capture the end of a pause
			session.add(Turns(
				GameID=GID,
				Round=currentGame.GameRound,
				TurnType="Pause",
				EventID=newEvent.EventID,
				TurnTime=getTimeDelta(newEvent.EventTime,previousState.EventTime)))
		#else if we're coming off of a strategic
		elif currentGame.GameState=="Strategic":	#we're ending a strategic action
			session.add(
				Turns(
					GameID=GID,
					Round=currentGame.GameRound,
					TurnType="Strategic",
					EventID=newEvent.EventID,
					TurnTime=getTurnTime(GID,newEvent,previousState,session),
					StrategicActionInfo=0,
					StrategyCardName=previousState.StrategyCardName,
					StrategyCardNumber=previousState.StrategyCardNumber
				)
			)
			#update the gamestate to reflect no stratergy card
			currentGame.GameStrategyNumber=None
			currentGame.GameStrategyName=None

			
		previousState.EventLink=newEvent.EventID	#update our previous event, event link
		currentGame.GameState=state	#update teh current game phase
		session.commit()	#commit all changes

def getFactionAndStrat(GID):
	#returns teh acting strategy faction and active strategy card number and name as a tuple (faction,number,name) for the current game during a strategic state
	with Session() as session:
		actFact=session.scalars(select(Factions).where(
			Factions.GameID==GID,
			Factions.ActiveStrategy==1
		)).first()
		actStrategyNumber=session.scalars(select(Games).where(Games.GameID==GID)).first().GameStrategyNumber
		actStrategyName=session.scalars(select(Games).where(Games.GameID==GID)).first().GameStrategyName
	return(actFact,actStrategyNumber,actStrategyName)

def changeStateToStrat(GID,state,strat,faction):
	#this function changes teh state, ending the current state (gamestate "action") and starting a new state (state "strategic")
	#this funtion is only called when changing the state from action to strategic
	##inputs
	#GID- game ID number
	#state = string for the state we are chaning to (always "Strategic")
	#strat = strategey card number being used
	#faction = the faction name executing the strategic action
	#this function will-
	#create an endstate event for the previous state (always "active")
	#create a startstate event for teh strategic state
	#change teh current gamestate
	#chagne teh current gamestrategynumber
	#changethecurrent game strategyname
	#change the current faction activestrategy
	'''
		GID -Game
		State - "Strategic"
		strat - stratnumber
	updates the state of the current game when called for a strategic action.  creates an event to end the current state and start a new state tracking the strategic action
	new state is equal to "state" value passed into function
	'''
	with Session() as session:
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()	#get teh current game
		#find the old start event
		oldStartEvent=session.scalars(select(Events).where(
				Events.GameID==GID,
				Events.EventType=="StartState",
				Events.StateData==currentGame.GameState
			).order_by(Events.EventTime.desc())).first()
		#find the actingfaction
		actFact=session.scalars(select(Factions).where(
			Factions.GameID==GID,
			Factions.FactionName==faction
			)).first()
		#create an end event for the previous state
		newEndEvent=Events(
			GameID=GID,
			EventType="EndState",
			PhaseData=currentGame.GamePhase,
			StateData=currentGame.GameState, 
			Round=currentGame.GameRound,
			FactionName=faction,
			EventLink=oldStartEvent.EventID
			)	
		#create a new event for the strategic state change
		newStartEvent=Events(
			GameID=GID,
			EventType="StartState",
			PhaseData=currentGame.GamePhase,
			StateData=state, 
			Round=currentGame.GameRound,
			FactionName=faction,
			StrategyCardNumber=strat,
			StrategyCardName=strategyNameDict[strat],
			) 	#add an event to start the current phase
		session.add(newEndEvent)
		session.add(newStartEvent)
		#create a turn event
		session.flush()
		#update eventlinks
		oldStartEvent.EventLink=newEndEvent.EventID
		#get the start event for the newEndEvent and assgne to event link
		#update teh game state
		currentGame.GameState=state	#update teh current game state to strategic
		#update the game strategynumber to the selected strat
		#we are udpading gamedata and investigating how we know what strategy card we're using
		currentGame.GameStrategyNumber=strat
		currentGame.GameStrategyName=strategyNameDict[strat]
		#set teh activefaction activestrategy =1
		actFact.ActiveStrategy=1
		session.commit()

def createSetup(GID):
	#called once at the beginning of the game when transitioning from setup.  Creates all the necessary things from the setup phase.
	with Session() as session:
		#baseGame=session.scalars(select(Games).where(GameID==GID)).first()
		#create a new phase start event
		newSetup=Events(
			GameID=GID,
			Round=0,
			PhaseData="Setup",
			StateData="Active",
			EventType="StartPhase"
		)
		#create a gamestart event
		newGame=Events(
			GameID=GID,
			Round=0,
			PhaseData="Setup",
			StateData="Active",
			EventType="GameStart"
		)
		#create a new start state event
		newState=Events(
			GameID=GID,
			EventType="StartState",
			PhaseData="Setup",
			StateData="Active", 
			Round=0
		)
		session.add(newState)
		session.add(newSetup)
		session.add(newGame)
		#end the setup phase this commits our session
		endPhase(GID,False,session)

def endPhase(GID,gameover,session=Session()):
	'''
		ends the current phase and cycles to the next phase
		if gameover==true, does not cycle to the next phase
	'''
	#get the current game for datause
	currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
	#get the previous phase start for elinking
	startPhaseEvent=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartPhase",Events.PhaseData==currentGame.GamePhase).order_by(Events.EventTime.desc())).first()
	#create the new event
	stopPhaseEvent=Events(
		GameID=GID,
		EventType="EndPhase",
		PhaseData=currentGame.GamePhase,
		Round=currentGame.GameRound,
		EventLink=startPhaseEvent.EventID,
		StateData=currentGame.GameState			
		)
	#add and flush the event
	session.add(stopPhaseEvent)
	session.flush()
	#assign the matching eventID
	startPhaseEvent.EventLink=stopPhaseEvent.EventID
	
	#create a new turn for ending the phase
	newTurn=Turns(
		GameID=GID,
		TurnTime=getTurnTime(GID,startPhaseEvent,stopPhaseEvent,session),
		TurnType="Phase",
		PhaseInfo=currentGame.GamePhase,
		Round=currentGame.GameRound,
		EventID=stopPhaseEvent.EventID
	)

	#if we are ending the game, we don't want to call "startPhase"
	if gameover:
		
		#check tos ee if we need to 'unpause'
		if currentGame.GameState=="Pause":
			#add an unpause event and pause turn
			changeState(GID,"Active")
			#move to an unpause state
		#find the active faction
		
		#if we are in the middle of someone's turn
		if currentGame.GamePhase=="Action":
			#find the acive player
			active=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first()
			#set them to inactive
			print(f'Were doing a phase end')
			active.Active=0
			#if we are in someones turn, we need to end their turn and not start a new one
			#PassTurn
			startEvent=session.scalars(select(Events).where(Events.FactionName==active.FactionName,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			#create the "end turn" event
			stopEvent=Events(
				GameID=GID,
				EventType="EndTurn",
				FactionName=active[0].FactionName, 
				TacticalActionData=0,
				Round=currentGame.GameRound,
				EventLink=startEvent.EventID,
				PhaseData=currentGame.GamePhase,
				StateData=currentGame.GameState,
				)
			#add it and flush it
			session.add(stopEvent)
			session.flush()
			#update startEvent link
			startEvent.EventLink=stopEvent.EventID
			#create the turn entry
			newTurn=Turns(
				GameID=GID,
				TurnTime=getTurnTime(GID,startEvent,stopEvent,session),
				TurnType="Tactical",
				TacticalActionInfo=0,
				PhaseInfo=currentGame.GamePhase,
				Round=currentGame.GameRound,
				EventID=stopEvent.EventID
			)
			session.add(newTurn)
		currentGame.GamePhase="Completed"
		session.commit()
	#if we're not ending the game
	if not gameover:
		#perform all the start actions and commit the session
		startPhase(GID,session)

#####################	Create Functions 	#################################

def createNewGame(gameConfig,gameDate=gdate):
	'''
	creates a new game with a default date of today
	adds factions to the faction table with the new game GID
	assigns the first speaker
	gameconfig is an array of tuples (factionname,(userID,speakerOrder))
	returns the newly created gameID
	'''
	with Session() as session:
		#create thew new game
		newGame=Games(GameDate=gameDate)
		session.add(newGame)
		session.flush()
		#add the factions to the game
		for item in gameConfig:
			#find the username of the faction id
			uName=session.scalars(select(Users).where(Users.UserID==item[1][0])).first().UserName
			#add the particular faction to the session, set the first person as speaker
			session.add(Factions
			   (FactionName=item[0],
				UserID=item[1][0],
				GameID=newGame.GameID,
				TableOrder=item[1][1],
				UserName=uName,
				Speaker= {1:1}.get(item[1][1],0)
				))
		#add a speaker event if it's the actual speaker
		{1:lambda:session.add(Events(GameID=newGame.GameID,EventType="Speaker",FactionName=item[0], Round=0))}.get(item[1][1],lambda:None)()
		session.commit()

def createUsers():
	#modify when we create a new user (deprecate)
	with Session() as session:
		session.add(Users(UserName="Charlie"))
		session.add(Users(UserName="Nathan"))
		session.add(Users(UserName="Sunny"))
		session.add(Users(UserName="GRRN"))
		session.add(Users(UserName="Jakers"))
		session.add(Users(UserName="Hythem"))
		session.commit()

def createPlayer(pName):
	'''
		adds a new player to the users list
	'''
	with Session() as session:
		#if len(session.scalars(select(Users).where(Users.UserName==pName)).all())==0:
		users=session.scalars(select(Users.UserName)).all()
		uLower=[user.lower() for user in users]
		if uLower.count(pName.lower())==0:
			newPlayer=Users(UserName=pName)
			session.add(newPlayer)
			print(f'Player {pName} added')
		else:
			print(f'Player {pName} already exists')
		session.commit()

def createNewUser(GID,uName):
	'''creates a new user and adds to db'''
	with Session() as session:
		session.add(Users(Username=uName))
		session.commit()
def getWinData(GID):
	'''
	returns the winning faction and winning user objects in a format {wFaction:faction, wUser: user}
	'''
	with Session() as session:
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		wFaction=session.scalars(select(Factions).where(
			Factions.GameID==GID,
			Factions.FactionName==gameBase.GameWinner
		)).first()
		wUser=session.scalars(select(Users).where(Users.UserID==wFaction.UserID)).first()
	return {'wFaction':wFaction,'wUser':wUser}

def getTimeDelta(endTime,startTime):
	#given T1 and T2, returns the delta in seconds as an int
	return abs((endTime-startTime).total_seconds())

#####################helper functions for initial testing####################

def restart():
	#clears the existing DB and creates the new one
	clearAll()
	createNew()

'''

'''

if __name__=="__main__":
	if len(sys.argv)>1:
		safemode=sys.argv[1]
	else:
		safemode="fuck you"
	#just a little helper function
	if safemode=="off":
		#restart()
		#timeConvert()
		print("restart complete")
		#new_game(1)
		#print("new Game created")
		#initiativeEvent(1)
		#gameStart(1)

		
		
	else:
		#roundMaker(1)
		print("safe mode enabled")

