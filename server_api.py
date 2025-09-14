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

def massUpdate(GID,stmts):
	'''
		this function receives a batch of statements to be updated. the statements are executed then committed
		stmts: list of update statements
		
	'''
	with Session() as session:
		for stmt in stmts:
			#print(f'Executing statment: {stmt}')
			session.execute(stmt)
		session.commit()
	

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
	
def findStrat(GID):
	'''
		returns the (num,name) strategy of the most recent state
	'''
	with Session() as session:
		strat=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState",Events.StateData=="Strategic").order_by(Events.EventID.desc())).first().MiscData
		return (strat,strategyNameDict[strat])

def findActiveStrat(GID):
	'''
		returns the name of whoever is up for the current strategic action
		find all events that are stateStart strategic, startTurn 2, endturn  1 2
		use the most recent event to determine who's next
			if stateStart = active faction
			if startturn 2 - that faction
			if endturn - the next faction findNextSpeakerOrderByName(GID,thisfaction,name)
	'''
	with Session() as session:
		stratEvent=session.scalars(select(Events).where((Events.GameID==GID)&(
		((Events.EventType=="StartState") & (Events.StateData=="Strategic"))|
		((Events.EventType=="StartTurn") & (Events.MiscData==2))|
		((Events.EventType=="EndTurn") & ((Events.MiscData==1) | (Events.MiscData==2))))).order_by(Events.EventID.desc())).first()	#find the strategic event that is driving our action
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
	
def updateTime(GID,faction,fwd_bwd=1):
	'''
	called when ending a turn
	finds the time delta and applies it to the factions total time
	needs to count the number of pauses
	should have a:
		"get_turn_time"
		get_pause_time which returns the time spent paused during a turn (totals)
		get_combat_time which returns the time spent in combat during a turn (totals)
		total time should be:
		get_turn_time - get_pause_time
	
	'''
	with Session() as session:
		#get teh start and stop time marks, then subtract them to get the full time of the turn
		#do we need faction in here?
		#turnStart=session.scalars(select(Events).where(Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	#most recent start
		#turnStop=session.scalars(select(Events).where(Events.FactionName==faction,Events.GameID==GID,or_(Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID.desc())).first() #most recent stop
		
		#most recent start
		turnStart=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	
		#find the stop associated with this start
		turnStop=session.scalars(select(Events).where(Events.GameID==GID,Events.EventLink==turnStart.EventID)).first() 
		#calculate the time between the two events
		turnTime=(turnStop.EventTime-turnStart.EventTime).total_seconds()	#we are now doing total seconds and storing as an int, rather than a datetime
		
		#subtract out any pauses/combats
		turnTime-=getPauseTime(GID,turnStart.EventID,turnStop.EventID)
		#find the faction we're doing the time modification for
		actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		
		#determine if this is a normal time add or if we're undoing a turn
		if fwd_bwd==-1:
			#print(f'subtracting {faction} time by {turnTime} from {actFact.TotalTime} to {actFact.TotalTime-turnTime}')
			session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==faction).values(TotalTime=actFact.TotalTime-turnTime))
		else:
			#print(f'adding {faction} time by {turnTime} from {actFact.TotalTime} to {actFact.TotalTime+turnTime}')
			session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==faction).values(TotalTime=actFact.TotalTime+turnTime))

		session.commit()


def undoEndStrat(GID):
	'''
		this button can only be pressed on the Strategic Action Screen
		it should follow the nextStrategicAction logic
			if startstate = 
				'state=active
				'undo-start state strategic
				'undo-end state active
				return to phase selector
				
			if startturn 2 - the previous "end turn 1/2" faction
				'undo-startturn -2
				'endo-endturn 1 or 2
				'subtract time
				return phase selector
	'''
	with Session() as session:
		stratEvent=session.scalars(select(Events).where((Events.GameID==GID)&(
		((Events.EventType=="StartState") & (Events.StateData=="Strategic"))|
		((Events.EventType=="StartTurn") & (Events.MiscData==2)))).order_by(Events.EventID.desc())).first()	#find the strategic event that is driving our action
		#print(f'SE: {stratEvent.EventID} PE: {stratEvent.EventID-1}')
		if (stratEvent.EventType!="StartState"):
			prevFaction=session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==stratEvent.EventID-1, Events.EventType=="EndTurn")).first().FactionName	#if it's a start turn event, we want the end turn faction name
	#clean this up, we don't need to exit the session here.
	if (stratEvent.EventType=="StartState") & (stratEvent.StateData=="Strategic"):#we accidentally entered into strat mode
		stmt=[update(Games).where(Games.GameID==GID).values(GameState="Active")]	#change the game state
		stmt.append(update(Events).where(Events.GameID==GID, Events.EventID==stratEvent.EventID).values(EventType="Correct-StartState"))	#change the start state envent
		stmt.append(update(Events).where(Events.GameID==GID, Events.EventType=="EndState",Events.EventID==stratEvent.EventID-1).values(EventType="Correct-EndState"))	#change the previous event, which is the end state
		stmt.append(insert(Events).values(GameID=GID,EventType="CorrectTurn",Round=getRound(GID)))	#log the turn correction
		massUpdate(GID,stmt)	#perform a mass update
	elif (stratEvent.EventType=="StartTurn") & ((stratEvent.MiscData==2) | (stratEvent.MiscData==1)):	#we accidentally ended a turn in strat mode
		updateTime(GID,prevFaction,-1)	
		stmt=[update(Events).where(Events.GameID==GID, Events.EventID==stratEvent.EventID).values(EventType="Correct-StartTurn")]	#change the start state envent
		stmt.append(update(Events).where(Events.GameID==GID, Events.EventType=="EndTurn",Events.EventID==stratEvent.EventID-1).values(EventType="Correct-EndTurn"))
		stmt.append(insert(Events).values(GameID=GID,EventType="CorrectTurn",Round=getRound(GID)))	#log the turn correction
		massUpdate(GID,stmt)	#perform a mass update
		
def undoEndTurn(GID,faction):
	'''
	#need to update to reflect strategic Action
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
	#check to see if we're at the top of the round, e.g., we can't undo wihtout going back a round
	passing=["EndTurn","PassTurn","StratEnd"]	#add StratEnd
	#print(f'-Starting undo for {faction} in game {GID}')
	with Session() as session:
		
		####we need to unwind this knot
		#print(f'-Gathering Data')
		curRound=getRound(GID)
		#print(f'-Current round: {GID}')
		prev_end1=session.scalars(
			select(Events).where(
				Events.GameID==GID,
				or_(Events.EventType==passing[0],Events.EventType==passing[1],Events.EventType==passing[2])).order_by(Events.EventID.desc())).all()
		for thing in prev_end1[:3]:
			print(f'{thing.EventID} - {thing.EventType}')
		prev_end=prev_end1[0]
		prev_fact=prev_end.FactionName	#avoid lazy loading
		prev_EID=prev_end.EventID
		prev_EType=prev_end.EventType
		print(f'Undo Type: {prev_EType} - {prev_end.EventType}')
		if prev_end is None:
			#print(f'-Cant go beyond first round')
			return "None"
		elif curRound>prev_end.Round:
			#print(f'-previous round {prev_end.Round} less than current {curRound}')
			return "None"
			
		#do major gamestate updates
		session.add(Events(GameID=GID,EventType="CorrectTurn", Round=getRound(GID)))	#create the event marking a turn correction ("CorrectTurn"
		#print(f'-Checking for pass')
		if prev_end.EventType=="PassTurn":		#if we're undoing a pass, update the pass status of the player that passed
			#print(f'-Updating {prev_end.FactionName} status to not passing')
			session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==prev_end.FactionName).values(Pass=False))
		elif prev_end.EventType=="StratEnd":	#if we're undoing a strategic action, it's here
			print(f'STRATEGIC ACTION UNDO')
			#find which faction strategy was previously used
			if prev_end.MiscData==session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==prev_end.FactionName)).first().Strategy1:
				print(f'STRAT 1')
				session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==prev_end.FactionName).values(StrategyStatus1=1))	#update that back to available
			else:
				print(f'STRAT 2')
				session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==prev_end.FactionName).values(StrategyStatus2=1))	#update that back to available
			print(f'Back to strat phase')
			session.execute(update(Games).where(Games.GameID==GID).values(GameState="Strategic"))	#update the state back to strategic
			session.execute(update(Events).where(Events.GameID==GID,Events.EventID==prev_end.EventID).values(EventType="Correct-StratEnd"))	#correct teh strategic action end
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="StartState").order_by(Events.EventID.desc())).first().EventType="Correct-StartState"
			session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="EndState").order_by(Events.EventID.desc())).first().EventType="Correct-EndState"
			#add correction fo endstate
			print(f'Find old data')
			prev_end=session.scalars(select(Events).where(Events.GameID==GID,Events.EventID==prev_end.EventID-1,Events.EventType=="EndTurn")).first()	#update previous end to be the previous faciton's end turn (strat)
			
			prev_fact=prev_end.FactionName
			prev_EID=prev_end.EventID
			prev_EType=prev_end.EventType
			print(f'{prev_EID} - {prev_fact} - {prev_EType}')
		session.commit()
	#update time here, now that we know the previous faction
	#print(f'-Updating the time for {prev_end.FactionName}')
	updateTime(GID,prev_fact,-1)		#we need to find this again for stratEnd.  it's the end turn faction and it's prevend-1
	#print(f'-Time updated')
	#update the current turn facionts start turn and the previous turn factions end/pass turn recent start/endturn events
	with Session() as session:
		#modify the "active faction" start event
		#faction is the active faction's name
		print(f'-modifying start turn and active status for {faction}')
		
		last_start=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	#find the last startturn (this will be now active)
		session.execute(update(Events).where(Events.GameID==GID,Events.EventID==last_start.EventID).values(EventType="Correct-StartTurn"))	#clear the previous start tun
		newActive=findNext(GID,-1)	#find's who was the previous active faction
		session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==faction).values(Active=False))	#make the current active false (move to pass/end
		#modify the "previous faction" end event
		#print(f'-modifying {prev_end.EventType} and active status for {prev_end.FactionName}')
		session.execute(update(Events).where(Events.EventID==prev_EID).values(EventType="Correct-"+prev_EType))	#correct the previous end or pass turn
		session.execute(update(Factions).where(Factions.GameID==GID,Factions.FactionName==newActive).values(Active=True))	#update the current active to prev
		session.commit()
	
def endTurn(GID,faction,fPass,misc=0):
	'''
	
	ends a faction's turn, if it's a pass(1), updates passing
	start's the next faction's turn
	
	create the end/pass event
	update pass status
	ID next faction
	update total time
	call startTurn or, if all pass, end phase
	Assigns MiscData to default 0.  Endturn miscdatas: 3-combat, 2-secondary strat, 1-primary strat
	'''
	passing=["EndTurn","PassTurn"]
	#WE NEED TO ADD the EVENTLINK option for ending turn
	#print(f'{faction} is {passing[fPass]}')
	with Session() as session:
		#find the related start event
		startTurn=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction, Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()
		#create the end event
		endEvent=Events(GameID=GID,
			EventType=passing[fPass],
			MiscData=misc,
			FactionName=faction, 
			Round=getRound(GID),
			EventLink=startTurn.EventID)	#create the event
		session.add(endEvent)
		#make the changes so we can access that event ID
		session.flush()
		#if the faction is passing, update their status to passing
		if fPass:
			session.execute(update(Factions).where(Factions.FactionName==faction).values(Pass=True))
		#update the event link for our start faction
		startTurn.EventLink=endEvent.EventID
		session.commit()
	updateTime(GID,faction)	#updates total time with most recent turn
	nextFaction=findNext(GID)
	
	print(f'{nextFaction} - {type(nextFaction)}')
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
		actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		actFact.Active=True
		session.add(Events(GameID=GID,EventType="StartTurn",FactionName=faction, Round=getRound(GID)))
		session.commit()
	
def startStrat(GID,faction):
	'''
		creates a start event for the given faction
	'''
	with Session() as session:
		session.add(Events(GameID=GID,EventType="StartTurn",FactionName=faction,MiscData=2,Round=getRound(GID)))
		session.commit()

def closeStrat(GID):
	'''
		closes teh current strat in GID
	'''
	strat=findStrat(GID)	#find the strat in question
	with Session() as session:
		sFaction=session.scalars(select(Factions).where(Factions.GameID==GID,or_(Factions.Strategy1==strat[0],Factions.Strategy2==strat[0]))).first()	#find the faction related to this strat
		session.add(Events(GameID=GID,EventType="StratEnd",Round=getRound(GID),MiscData=strat[0],FactionName=sFaction.FactionName))	#create a close event
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
	#session.add(Events(GameID=GID,EventType="StartState",PhaseData=currentGame.GamePhase,StateData=state, MiscData=strat,Round=getRound(GID))) 	#add an event to start the current phase
	primsec={1:"Primary",2:"Secondary"}
	with Session() as session:
		previousStrat=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartState",
			Events.StateData=="Strategic"
			).order_by(Events.EventID.desc())).first()
			
		startEvent=session.scalars(select(Events).where(
			Events.GameID==GID,
			Events.EventType=="StartTurn",
			Events.FactionName==faction
			).order_by(Events.EventID.desc())).first()
		
		if session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().FactionName==faction:	#if the calling faction is the active faction, it's aprimary
			state=1	#primary strate
		else:	#else it's a secondary
			state=2	#secondary strat
		newEnd=Events(GameID=GID,EventType="EndTurn",MiscData=state,FactionName=faction, Round=getRound(GID),EventLink=startEvent.EventID,StrategyData=previousStrat.MiscData)	#create the event either a primary or secondary strategy
		session.add(newEnd)
		session.flush()	#flush to get data
		
		#create the turn event
		session.add(Turns(
			GameID=GID,
			TurnType="Strategic",
			TurnInfo=primsec[state],
			MiscData=strategyNameDict[previousStrat.MiscData],
			FactionName=faction,
			Round=getRound(GID),
			TurnTime=getTimeDelta(newEnd.EventTime,startEvent.EventTime),
			EventID=newEnd.EventID))
		startEvent.EventLink=newEnd.EventID	#update the linkage
		#stmt=insert(Events).values(GameID=GID,EventType="EndTurn",MiscData=state,FactionName=faction, Round=getRound(GID))
		session.commit()
	#massUpdate(GID,[stmt])
	updateTime(GID,faction) #update this factions' time on the clock

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

def boolEvent(GID,eType,pup):
	'''
	initiates a boolean (true/false) event with type eType and state of bool pup (Pause/UnPause (1/0))
	this is used by pause
	THis is going to be OBE
	'''
	eLink=None
	with Session() as session:
		#if we are unpausing, we need to find the most recent pause evnet to create the EventLink Data
		
		if ((eType=="Pause") & (pup==0)):
			#find the eventID of the start event
			pEvent=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause",Events.MiscData==1).order_by(Events.EventID.desc())).first()
			eLink=pEvent.EventID
		uPause=Events(GameID=GID, EventType=eType, MiscData=pup, Round=getRound(GID),EventLink=eLink)
		session.add(uPause)
		#if we're doing an unpause, add the event ID to the pause event
		if eLink is not None:
			session.flush()
			pEvent.EventLink=uPause.EventID
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
		session.add(Events(GameID=GID,EventType="Score",FactionName=faction,MiscData=points, Round=getRound(GID)))
		res=session.scalars(select(Factions).where(Factions.FactionName==faction,Factions.GameID==GID)).first()
		res.Score+=points
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
				
			[session.add(Events(GameID=GID,EventType="Initiative",FactionName=row.FactionName,MiscData=0, Round=getRound(GID)))
				for row in factions]	#add an event for all inits to 0
		
		elif newPhase=="Strategy":
			#end old round, start new round
			currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
			currentRound=currentGame.GameRound
			session.add(Events(GameID=GID,EventType="EndRound",MiscData=currentRound, Round=getRound(GID)))
			session.add(Events(GameID=GID,EventType="StartRound",MiscData=currentRound+1, Round=getRound(GID)+1))
			currentGame.GameRound+=1
			
		
		elif newPhase=="Status":
			#clear all of the "pass" status
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			for row in factions:
				row.Pass=0 #set all pass status to 0
				row.Active=0	#set all to inactive
			
		session.commit()
			
	#stop game needs to initiate a pause event if it's not already paused
def changeState(GID,state,strat=0):
	'''
	updates the state of the current game. called when changing pause-active-strategic
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
		
		#if we are coming off of a pause add a Turn for pause
		if currentGame.GameState=="Pause":	#if it's a pause, we want to capture the end of a pause
			session.add(Turns(
				GameID=GID,
				Round=getRound(GID),
				TurnType="Pause",
				EventID=newEvent.EventID,
				TurnTime=getTimeDelta(newEvent.EventTime,previousState.EventTime)))
		#else if we're coming off of a strategic
		elif currentGame.GameState=="Strategic":	#we're ending a strategic action
			pass
			#moving from pause-start may fuck us here
			#we'd have strat start-strat end-pause start - pause end - strat start -strat end
			#we may be better served with a startStrat eventtype
			
		previousState.EventLink=newEvent.EventID	#update our previous event, event link
		currentGame.GameState=state	#update teh current game phase
		session.commit()	#commit all changes

def changeStateStrat(GID,state,strat):
	'''
		GID -Game
		State - "Strategic"
		strat - stratnumber
	updates the state of the current game when called for a strategic action.  creates an event to end the current state and start a new state tracking the strategic action
	new state is equal to "state" value passed into function
	'''
	with Session() as session:
		#get teh current game
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()	#get teh current game
		session.add(Events(GameID=GID,EventType="EndState",PhaseData=currentGame.GamePhase,StateData=currentGame.GameState, Round=getRound(GID)))	#get add an event to end teh current state
		session.add(Events(GameID=GID,EventType="StartState",PhaseData=currentGame.GamePhase,StateData=state, MiscData=strat,Round=getRound(GID))) 	#add an event to start the current phase
		currentGame.GameState=state	#update teh current game phase
		session.commit()


def endPhase(GID,gameover):
	'''
		ends the current phase and cycles to the next phase
		if gameover==true, does not cycle to the next phase
	'''
	with Session() as session:
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		session.add(Events(GameID=GID,EventType="EndPhase",PhaseData=currentGame.GamePhase, Round=getRound(GID)))
		
		#if we are ending the game, we don't want to call "startPhase"
		if gameover:
			active=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).all()
			if len(active)>0:
				
				#check tos ee if we need to 'unpause'
				lastPause=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause").order_by(Events.EventID.desc())).all()
				if len(lastPause)>0:
					if lastPause[0].MiscData==1:
						session.add(Events(GameID=GID,EventType="Pause",MiscData=0, Round=getRound(GID)))
				active[0].Active=0
				#check to see if we need to end teh active player's turn
				turns=session.scalars(select(Events).where(Events.FactionName==active[0].FactionName,or_(Events.EventType=="StartTurn",Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID)).all()
				if turns[len(turns)-1].EventType=="StartTurn":
					session.scalars(select(Factions).where(Factions.FactionName==active[0].FactionName)).first().Pass=True
					session.add(Events(GameID=GID,EventType="PassTurn",FactionName=active[0].FactionName, Round=getRound(GID)))
					#add turn row
					#session.add(Turns(GameID=GID,TurnType
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

def getTimeDelta(t1,t2):
	#given T1 and T2, returns the delta in seconds as an int
	return abs((t1-t2).total_seconds())

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

