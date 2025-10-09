'''
	"backend" interface for teh server.  Includes all the functions called by the server when accessing the system
'''
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats, Base, Turns
from sqlalchemy import select, or_, and_, delete, update, insert
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect
from time import sleep
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

def findNextSpeakerOrderByName(GID,factionName):
	'''
		returns the next factionin table order starting with the identified factionname
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

def getRound(GID):
	'''
	returns the round of the current game
	'''
	return Session().scalars(select(Games).where(Games.GameID==GID)).first().GameRound

def findNext(GID,fwd_bwd=1):
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
			
def getPauseTime(GID,startEventID,stopEventID):
	'''
	finds the length of a pause
	finds all pauses with this faction
	finds all the pauses that occured since turnStart
	finds all the associated un-pauses
	calculates the time
	returns total_seconds() of the time delta
	'''
	pauseTime=dt.timedelta(0)
	with Session() as session:
		#find all pauses since this turn start
		#find all the pause and unpause events that occured between the start and stop event IDs
		pauseTime=0
		#find all the start pause events
		pauses=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState",Events.StateData=="Pause",Events.EventID>startEventID,Events.EventID<stopEventID).order_by(Events.EventID.desc())).all()
		#find the total time spent paused in these events
		pauseArray=[(session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==pause.EventLink)).first().EventTime-pause.EventTime).total_seconds() 
			for pause in pauses]
		#add up the pauses
		for pause in pauseArray:
			#print(f'Pause {pause}')
			pauseTime+=pause
			
	#print(f'Total Time: {pauseTime} - {type(pauseTime)}')
	return pauseTime

def findActiveStrat(GID):
	'''
		returns the factionname of the active faction for current strategic action
		find all events that are stateStart strategic, startTurn 2, endturn  1 2
		use the most recent event to determine who's next
			if stateStart & strategic = active faction, first entry into strategic actions
			if startturn & strategic - the faction that started the turn #HERE I think we cna remove this.  it doesn't make sense why e'd check for a secondary.  we are either starting the state or ending the turn
			if endturn & misc=1 - the next faction findNextSpeakerOrderByName(GID,thisfaction,name)
	'''
	with Session() as session:
		#find the strategic event that is driving our action
		stratEvent=session.scalars(select(Events).where((Events.GameID==GID)&(
			((Events.EventType=="StartState") & (Events.StateData=="Strategic"))|
			((Events.EventType=="StartTurn") & (Events.StateData=="Strategic"))|
			((Events.EventType=="EndTurn") & ((Events.StratgicActionInfo==1) | (Events.StratgicActionInfo==2))))).order_by(Events.EventID.desc())).first()	
		if stratEvent.EventType=="StartState":	#if it's teh startstate, that means it's the active faction
			return session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().FactionName
		elif stratEvent.EventType=="StartTurn":	#if it's the start turn, that means it's the faction that started with "strategic action turn"
			return stratEvent.FactionName
		else:	#otherwise, it's an end event and it's the next person in speaker order
			return findNextSpeakerOrderByName(GID,stratEvent.FactionName)
			
def getFactions(GID):
	'''
		returns a list of the factions
	'''
	with Session() as session:
		return session.scalars(select(Factions).where(Factions.GameID==GID)).all()

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

def getTurnTime(GID,startEvent,stopEvent):
	#returns the totalseconds for teh turn
	#given the start and stop events, calcualtes the turn time
	#using the start and stop event ids, determines total pause time
	#subrtracts pause time from turn time and returns
	
	turnTime=(stopEvent.EventTime-startEvent.EventTime).total_seconds()	#we are now doing total seconds and storing as an int, rather than a datetime
	#subtract out any pauses/combats
	turnTime-=getPauseTime(GID,startEvent.EventID,stopEvent.EventID)
	print(f'TurnTime: {turnTime}')
	return turnTime

def updateTime(GID,faction,fwd_bwd=1):
	#returns the factions new total time
	#GID - Game ID
	#faction - FactionName (str)
	#fwd-bwd - (1) if adding time, (-1) if subtracting time
	#calcuates the total time of (faction) between (faction's) most recent
	#start turn and end turn
	#will subtract out any pause time using getPauseTime
	with Session() as session:
		#get teh start and stop time marks, then subtract them to get the full time of the turn
		
		#factions most recent start
		turnStart=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	
		#find the stop associated with this start
		#factions most recent stop
		turnStop=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==turnStart.EventID)).first()
		#calculate the time between the two events
		turnTime=(turnStop.EventTime-turnStart.EventTime).total_seconds()	#we are now doing total seconds and storing as an int, rather than a datetime
		
		#subtract out any pauses/combats
		turnTime-=getPauseTime(GID,turnStart.EventID,turnStop.EventID)
		#find the faction we're doing the time modification for
		actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		
		#determine if this is a normal time add or if we're undoing a turn
		totalTime=actFact.TotalTime+(fwd_bwd*turnTime)

	return totalTime


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
			#update the game state
			baseGame.GameState="Active"
			#clear the game strats
			baseGame.GameStrategyNumber=None
			baseGame.GameStrategyName=None
			print(f'undid a strat-tact')
		#determine if we are going back to a previous strategic action
		elif (prevEnd.StrategicActionInfo is not None):
			#find the previous start
			prevStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			#correct previous start
			prevStart.EventType="Correct-StartTurn"
			#correct prevEnd
			prevEnd.EventType="Correct-EndTurn"
			prevEnd.EventLink=None
			#find previously active Faction
			prevFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first()
			#update that factions total time
			prevFact.TotalTime=updateTime(GID,prevFact,1)
			#update current faction active status
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().Active=0
			#update the previous faction active status
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevFact.FactionName)).first().Active=1
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
		elif baseGame.Round>prevEnd.Round:
			#print(f'-previous round {prev_end.Round} less than current {curRound}')
			return "None"
		#chedk to see if we are doing a basic active-active undo
		if ((prevEnd.StateData=="Active")&(baseGame.GameState=="Active")):
			#correct the start of the current turn
			currStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			currStart.EventType="Corrected-StartTurn"
			#correct the previous faction end turn
			prevEnd.EventType="Corrected-EndTurn"
			#correct the event linked to the prevEnd
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==prevEnd.EventLink)).first().EventLink=None
			#correct prevEnd's event link
			prevEnd.EventLink=None
			#correct the previous faction time
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().TotalTime=updateTime(GID,prevEnd.FactionName,-1)
			#update the active faction
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().Active=0
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().Active=1
			#check to see if it was a pass
			if prevEnd.TacticalActionInfo==1:
				#update the pass status
				session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().Pass=0
			#correct the previous turn entry
			session.scalars(select(Turns).where(Turns.GameID==GID,Turns.EventID==prevEnd.EventID)).first().TurnType="Corrected-Tactical"
		#see if we're going from a active start to a strateigc end
		elif ((prevEnd.StateData=="Strategic") & (baseGame.GameState=="Active")):
			#correct the start of the current turn
			currStart=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartTurn").order_by(Events.EventTime.desc())).first()
			currStart.EventType="Corrected-StartTurn"
			#correct the previous faction end turn
			prevEnd.EventType="Corrected-EndTurn"
			#correct the event linked to the prevEnd
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==prevEnd.EventLink)).first().EventLink=None
			#correct prevEnd's event link
			prevEnd.EventLink=None
			#correct the previous faction time
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().TotalTime=updateTime(GID,prevEnd.FactionName,-1)
			#update the active faction
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().Active=0
			session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prevEnd.FactionName)).first().Active=1
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
			#correct the stratend turn entry
			session.scalars(select(Turns).where(Turns.GameID==GID,Turns.EventID==stratEnd.EventID)).first().TurnType="Corrected-Strategic"
		#any undo originating from the strategic action screen will call undoEndStrat
		#do major gamestate updates
		session.add(Events(GameID=GID,EventType="CorrectTurn", Round=baseGame.Round, StateData=baseGame.GameState, PhaseData=baseGame.GamePhase))	#create the event marking a turn correction ("CorrectTurn"
		session.commit()
	#update time here, now that we know the previous faction
	#print(f'-Updating the time for {prev_end.FactionName}')
	#update the current turn facionts start turn and the previous turn factions end/pass turn recent start/endturn events

def endTurn(GID,faction,misc=0):
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
	turnType={0:"Action",1:"Pass",2:"Combat"}			#this is used to determine what type of turn occured

	with Session() as session:
		#find the related start event
		startTurn=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction, Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()
		#create the end event
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		endEvent=Events(GameID=GID,
			EventType="EndTurn",
			TacticalActionInfo=misc,
			FactionName=faction, 
			Round=getRound(GID),
			EventLink=startTurn.EventID,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState)	#create the event
		session.add(endEvent)
		#make the changes so we can access that event ID
		session.flush()
		#if the faction is passing, update their status to passing
		if misc==1:
			session.execute(update(Factions).where(Factions.FactionName==faction).values(Pass=True))
		#update the event link for our start faction
		startTurn.EventLink=endEvent.EventID
		
		#create the endturn turn entry
		turnEntry=Turns(
					GameID=GID,
					TurnTime=getTurnTime(GID,startTurn,endEvent),
					Round=getRound(GID),
					FactionName=faction,
					TurnType="Tactical",
					TacticalActionInfo=misc,
					EventID=endEvent.EventID
					)
		#add the turn entry
		session.add(turnEntry)
		#update the faction's time
		session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first().TotalTime=updateTime(GID,faction)
		session.commit()

	#get the enxt faction
	nextFaction=findNext(GID)
	
	#check to see if we can move on or if there are still more turns this tactical phase
	if nextFaction=="none":
		#print("Ending phase due to no players left")
		endPhase(GID,False)
	else:
		startFactTurn(GID,nextFaction)

def startFactTurn(GID,faction):
	'''
	starts a faction's turn
	create an event for turn start
	update the active faction
	'''
	with Session() as session:
		#this needs to be an update/execute statement
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		actFact.Active=True
		newEvent=Events(GameID=GID,
			EventType="StartTurn",
			FactionName=faction, 
			Round=getRound(GID),
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState)
		session.add(newEvent)
		session.commit()
	
def startStrat(GID,faction):
	'''
		creates a start stratevent for the given faction
	'''
	with Session() as session:
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#note strategicactioninfo is always 2, since this is always a secondary action.  THe start of the strategy turn is captured as a generic start turn and is indicated 
		newEvent=Events(
			GameID=GID,
			EventType="StartTurn",
			FactionName=faction,
			StrategicActionInfo=2,
			Round=getRound(GID),
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState,
			StrategyCardNumber=int(gameBase.GameStrategyNumber),
			StrategyCardName=strategyNameDict[int(gameBase.GameStrategyNumber)]
			)
		session.add(newEvent)
		session.commit()

def closeStrat(GID):
	'''
		closes teh current strat in GID
	'''
	
	with Session() as session:
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		strat=(gameBase.GameStrategyNumber,gameBase.GameStrategyName)
		sFaction=session.scalars(select(Factions).where(Factions.GameID==GID,or_(Factions.Strategy1==strat[0],Factions.Strategy2==strat[0]))).first()	#find the faction related to this strat
		#this is missing a stratstart event, why are we doing a "stratEND"?instead just a turn and a normal stateEnd?
		'''
		newEvent=Events(
			GameID=GID,
			EventType="StratEnd",
			Round=getRound(GID),
			FactionName=sFaction.FactionName,
			PhaseData=gameBase.GamePhase,
			StateData=gameBase.GameState,
			StrategyCardNumber=strat[0],
			StrategyCardName=strat[1],
			StrategicActionInfo=0)	#create a close event
		session.add(newEvent)
		session.flush()
		'''
		#create the overall strategy turn
		if strat[0]==sFaction.Strategy1:	#find teh appropriate strat and show it as closed
			sFaction.StrategyStatus1=0
		else:
			sFaction.StrategyStatus2=0
		session.commit()
	
def endStrat(GID,faction):
	#updated to add eventlinks, strategy data
	#updated to create turn data for a strategic-primary/secondary-stratID turn
	'''
		ends a strategic action for a faction
		state indicates if it's teh 1 "primary" or 2 "secondary" action that is ending
		returns the "next faction" factionname
	'''
	#we need to know what strategic action is being ended
	#previous startstatestrategic will contain the strat number under misc data
	
	with Session() as session:
		#this finds the most recent strategic state start event
		previousStrat=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartState",
			Events.StateData=="Strategic"
			).order_by(Events.EventID.desc())).first()
		#this finds teh most recent startturn event (e.g., whoevers turn just started)
		startEvent=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartTurn",
			Events.FactionName==faction
			).order_by(Events.EventID.desc())).first()
		#this is the basegame event used to extract and capture game info
		gameBase=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#grab a base faction to capture faction info
		factionInfo=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction ))

		#determine if it's the primary or secondary action
		if session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().FactionName==faction:	#if the calling faction is the active faction, it's aprimary
			state=1	#primary strate
		else:	#else it's a secondary
			state=2	#secondary strat
		#create the endturn event
		newEnd=Events(
		GameID=GID,
		EventType="EndTurn",
		StrategicActionInfo=state,
		FactionName=faction,
		Round=getRound(GID),
		EventLink=startEvent.EventID,
		StrategyCardName=previousStrat.StrategyCardName,
		StrategyCardNumber=previousStrat.StrategyCardNumber,
		PhaseData=gameBase.GamePhase,
		StateData=gameBase.GameState,
		ScoreTotal=factionInfo.Score)	#create the event either a primary or secondary strategy
		session.add(newEnd)
		session.flush()	#flush to get data
		
		#create the turn event
		session.add(Turns(
			GameID=GID,
			TurnType="Strategic",
			StrategicActionInfo=state,
			StrategyCardNumber=previousStrat.StrategyCardNumber,
			StrategyCardName=previousStrat.StrategyCardName,
			FactionName=faction,
			Round=getRound(GID),
			TurnTime=getTimeDelta(newEnd.EventTime,startEvent.EventTime),
			EventID=newEnd.EventID))
		startEvent.EventLink=newEnd.EventID	#update the linkage
		#update the faction time
		session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first().TotalTime=updateTime(GID,faction)
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
		session.commit()
			
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
		session.add(Events(GameID=GID,EventType="Speaker",FactionName=faction, Round=getRound(GID)))
		#update state
		session.execute(update(Factions).where(Factions.GameID==GID).values(Speaker=False))
		session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==faction).values(Speaker=True))
		session.commit()
		
def adjustPoints(GID,faction,points):
	'''
	adjusts the points for a faction by "points".  Can be positive or negative, creates event and then updates the scores
	'''
	with Session() as session:
		res=session.scalars(select(Factions).where(Factions.FactionName==faction,Factions.GameID==GID)).first()
		res.Score+=points
		session.flush()
		session.add(Events(GameID=GID,EventType="Score",FactionName=faction,Score=points,ScoreTotal= res.Score,Round=getRound(GID)))
		session.commit()
		
def gameStart(GID):
	'''
	starts game by creting a start game event
	'''
	with Session() as session:
		#session.add(Events(GameID=GID,EventType="GameStart"))	#once setup phase is complete, we will need to remove this.
		session.add(Events(GameID=GID, EventType="StartPhase", PhaseData="Setup", Round=getRound(GID)))	#create the event
		session.commit()
			
def gameStop(GID,faction):
	'''
	ends the game by creating a stop game event
	'''
	endPhase(GID,True)
	with Session() as session:
		session.scalars(select(Games).where(Games.GameID==GID)).first().GameWinner=faction
		session.add(Events(GameID=GID,EventType="GameStop", Round=getRound(GID)))
		session.commit()
	
		
def startPhase(GID):
	'''
	when a phase ends, this moves us into the next phase
	creates an event for new phase start
	updates game table
	'''
	phase_order={"Setup":"Strategy","Strategy":"Action","Action":"Status","Status":"Agenda","Agenda":"Strategy"}
	with Session() as session:
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#if it's the setup phase, we need to add a gamestart event since the game is starting
		if (currentGame.GamePhase=="Setup"):
				session.add(Events(GameID=GID,EventType="GameStart", Round=getRound(GID)))
		#create new phase and update
		newPhase=phase_order[currentGame.GamePhase]	#use the dict to bump us to the next phase, separate so it persists
		currentGame.GamePhase=newPhase
		#start the phase event
		session.add(Events(GameID=GID, EventType="StartPhase", PhaseData=currentGame.GamePhase, Round=getRound(GID)))	#create the event
		session.commit()
	
	phaseChangeDetails(GID,newPhase)

def phaseChangeDetails(GID,newPhase):
	'''
		called when we enter a new phase, this is where we do things like assign the new active player, remove initiatives, etc.
	'''
	with Session() as session:
		if newPhase=="Action":
			'''
				entering the action phase we need to automatically assign the active faction 
				and start their turn
			'''
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).first()
			startFactTurn(GID,activeFaction.FactionName)
		
		elif newPhase=="Agenda":
			'''
				clear all the initiatives
			'''
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			for row in factions:
				row.Initiative=0 #set all inits to 0

			#setting the initiatives to 0 is not an event	
			'''
			[session.add(Events(GameID=GID,EventType="Initiative",FactionName=row.FactionName,MiscData=0, Round=getRound(GID)))
				for row in factions]	#add an event for all inits to 0
				'''
		
		elif newPhase=="Strategy":
			#end old round, start new round
			currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
			currentRound=currentGame.GameRound
			session.add(Events(GameID=GID,EventType="EndRound", Round=getRound(GID)))
			session.add(Events(GameID=GID,EventType="StartRound", Round=getRound(GID)+1))
			currentGame.GameRound+=1
			
		
		elif newPhase=="Status":
			#clear all of the "pass" status
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			for row in factions:
				row.Pass=0 #set all pass status to 0
				row.Active=0	#set all to inactive
			
		session.commit()
			
	#stop game needs to initiate a pause event if it's not already paused
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
			Round=getRound(GID),
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
			Round=getRound(GID))) 	#add an event to start the current phase
		
		#if we are ending a pause add a Turn for pause
		if currentGame.GameState=="Pause":	#if it's a pause, we want to capture the end of a pause
			session.add(Turns(
				GameID=GID,
				Round=getRound(GID),
				TurnType="Pause",
				EventID=newEvent.EventID,
				TurnTime=getTimeDelta(newEvent.EventTime,previousState.EventTime)))
		#else if we're coming off of a strategic
		elif currentGame.GameState=="Strategic":	#we're ending a strategic action
			session.add(Turns(
				GameID=GID,
				Round=getRound(GID),
				TurnType="Strategic",
				EventID=newEvent.EventID,
				TurnTime=getTurnTime(GID,newEvent,previousState)),
				StrategicActionInfo=0,
				StrategyCardName=previousState.StrategyCardName,
				StrategyCardNum=previousState.StreategyCardNumber
				)
			#update the gamestate to reflect no stratergy card
			currentGame.GameStrategyNumber=None
			currentGame.GameStrategyName=None

			
		previousState.EventLink=newEvent.EventID	#update our previous event, event link
		currentGame.GameState=state	#update teh current game phase
		session.commit()	#commit all changes

def changeStateStrat(GID,state,strat,faction):
	#this function changes teh state, ending the current state (gamestate "action") and starting a new state (state "strategic")
	#strat is the strat number
	#this funtion is only called when changing the state from action to strategic
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
		oldStartEvent=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState",Events.StateData==currentGame.GameState).order_by(Events.EventTime.desc())).first()
		#create an end event for the previous state
		newEndEvent=Events(
			GameID=GID,
			EventType="EndState",
			PhaseData=currentGame.GamePhase,
			StateData=currentGame.GameState, 
			Round=getRound(GID),
			FactionName=faction,
			EventLink=oldStartEvent.EventID
			)	
		#create a new event for the strategic state change
		newStartEvent=Events(
			GameID=GID,
			EventType="StartState",
			PhaseData=currentGame.GamePhase,
			StateData=state, 
			Round=getRound(GID),
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
		session.commit()


def endPhase(GID,gameover):
	'''
		ends the current phase and cycles to the next phase
		if gameover==true, does not cycle to the next phase
	'''
	with Session() as session:
		#get the current game for datause
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		#get the previous phase start for elinking
		startPhase=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartPhase",Events.PhaseData==currentGame.GamePhase).order_by(Events.EventTime.desc())).first()
		#create the new event
		stopPhase=Events(
			GameID=GID,
			EventType="EndPhase",
			PhaseData=currentGame.GamePhase,
			Round=currentGame.Round,
			EventLink=startPhase.EventID,
			StateData=currentGame.GameState			
			)
		#add and flush the event
		session.add(stopPhase)
		session.flush()
		#assign the matching eventID
		startPhase.EventLink=stopPhase.EventID
		
		#create a new turn for ending the phase
		newTurn=Turns(
			GameID=GID,
			TurnTime=getTurnTime(GID,startPhase,stopPhase),
			TurnType="Phase",
			PhaseInfo=currentGame.GamePhase,
			Round=currentGame.Round,
			EventID=stopPhase.EventID
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
					Round=getRound(GID),
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
					TurnTime=getTurnTime(GID,startEvent,stopEvent),
					TurnType="Tactical",
					TacticalActionInfo=0,
					PhaseInfo=currentGame.GamePhase,
					Round=currentGame.Round,
					EventID=stopEvent.EventID
				)
				session.add(newTurn)
			currentGame.GamePhase="Completed"
		session.commit()
	
	if not gameover:
		startPhase(GID)

#####################	Create Functions 	#################################

def createNewGame(gameDate=gdate):
	'''
	creates a new game with a default date of today
	returns the newly created gameID
	'''
	with Session() as session:
		newGame=Games(GameDate=gameDate)
		session.add(newGame)
		session.commit()
		print ("GameID {}".format(newGame.GameID))
	return newGame.GameID

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
	
def addFactions(GID, gameConfig):
	'''
		adds users/factions to the game
		gameConfig=('faction':(userID,tableOrder))
	'''
	with Session() as session:
		for item in gameConfig:
			uName=session.scalars(select(Users).where(Users.UserID==item[1][0])).first().UserName
			session.add(Factions(FactionName=item[0],
			UserID=item[1][0],
			GameID=GID,
			TableOrder=item[1][1],
			UserName=uName))
		session.commit()

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
		#endPhase(1,0)
		#endPhase(1,0)
		
		
	else:
		#roundMaker(1)
		print("safe mode enabled")

