'''
"backend" interface for teh server.  Includes all the functions called by the server when accessing the system
'''
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats
from sqlalchemy import select, or_, delete, update
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect
from time import sleep
import sys

#modify when we create games
gdate=dt.date.today().strftime("%Y%m%d")

#update to reflect new game
UF_Dict={"Charlie":("Titans of Ul",4), "Hythem":("Mentak Coalition",3),
		"Sunny":("Embers of Muaat",2),"Nathan":("Vuil'Raith Cabal",1)}
Session=sessionmaker(engine)

#modify 
#GID 1 = winner screen
#GID 2 = action phases

#GID=1	#value used to identify current only during creating a enw game with script for testing



			
			

def get_speaker_order(GID,factions):
	'''
		returns an array of factions in table order starting with the speaker
	'''
	#this will sort by speaker for display
	tFaction=[]
	sFaction=factions[0]	#default here incase of no speaker selected
	#identify the speaker
	for faction in factions:
		tFaction.append(None)
		if faction.Speaker:
			sFaction=faction
	#print("%s %s"%(sFaction.FactionName,sFaction.TableOrder))
	#go through the faction list and order them in tableorder starting with the speaker
	for faction in factions:
		tFaction[(faction.TableOrder-sFaction.TableOrder)%len(factions)]=faction
		#print("%s %s %s"%(faction.FactionName,faction.TableOrder,(faction.TableOrder-sFaction.TableOrder)%len(factions)))
	return tFaction
			

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
	initiates a boolean (true/false) event with type eType and state of bool pup
	'''
	with Session() as session:
		session.add(Events(GameID=GID, EventType=eType, MiscData=pup))
		session.commit()

def newSpeaker(GID,faction):
	'''
	removes current speaker and assigns the given faction the speaker priority
	'''
	
	with Session() as session:
		#event
		session.add(Events(GameID=GID,EventType="Speaker",FactionName=faction))
		#update state
		res=session.scalars(select(Factions).where(Factions.Speaker==True)).all()
		for row in res:
			row.Speaker=False
		res=session.scalars(select(Factions).where(Factions.FactionName==faction)).first()
		res.Speaker=True
		session.commit()
		
def adjustPoints(GID,faction,points):
	'''
	adjusts the points for a faction by "points".  Can be positive or negative, creates event and then updates the scores
	'''
	with Session() as session:
		session.add(Events(GameID=GID,EventType="Score",FactionName=faction,MiscData=points))
		res=session.scalars(select(Factions).where(Factions.FactionName==faction,Factions.GameID==GID)).first()
		res.Score+=points
		session.commit()
		
def gameStart(GID):
	'''
	starts game by creting a start game event
	'''
	with Session() as session:
		#session.add(Events(GameID=GID,EventType="GameStart"))	#once setup phase is complete, we will need to remove this.
		session.add(Events(GameID=GID, EventType="StartPhase", PhaseData="Setup"))	#create the event
		session.commit()
	#move into the strat phase
	#startPhase(GID) #once setup phase is complete, we will need to remove this.
		
def gameStop(GID,faction):
	'''
	ends the game by creating a stop game event
	'''
	endPhase(GID,True)
	with Session() as session:
		session.scalars(select(Games).where(Games.GameID==GID)).first().GameWinner=faction
		session.add(Events(GameID=GID,EventType="GameStop"))
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
				session.add(Events(GameID=GID,EventType="GameStart"))
		#create new phase and update
		newPhase=phase_order[currentGame.GamePhase]	#use the dict to bump us to the next phase, separate so it persists
		currentGame.GamePhase=newPhase
		#start the phase event
		session.add(Events(GameID=GID, EventType="StartPhase", PhaseData=currentGame.GamePhase))	#create the event
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
			startTurn(GID,activeFaction.FactionName)
		
		elif newPhase=="Agenda":
			'''
				clear all the initiatives
			'''
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			for row in factions:
				row.Initiative=0 #set all inits to 0
				
			[session.add(Events(GameID=GID,EventType="Initiative",FactionName=row.FactionName,MiscData=0))
				for row in factions]	#add an event for all inits to 0
		
		elif newPhase=="Strategy":
			#end old round, start new round
			currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
			currentRound=currentGame.GameRound
			session.add(Events(GameID=GID,EventType="EndRound",MiscData=currentRound))
			session.add(Events(GameID=GID,EventType="StartRound",MiscData=currentRound+1))
			currentGame.GameRound+=1
			
		
		elif newPhase=="Status":
			#clear all of the "pass" status
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			for row in factions:
				row.Pass=0 #set all pass status to 0
				row.Active=0	#set all to inactive
			
		session.commit()
			
def changeState(GID,state):
	'''
	updates the state of the current game.  creates an event to end the current state and start a new state.
	new state is equal to "state" value passed into function
	'''
	with Session() as session:
		#get teh current game
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()	#get teh current game
		session.add(Events(GameID=GID,EventType="EndState",PhaseData=currentGame.GamePhase,StateData=currentGame.GameState))	#get add an event to end teh current state
		session.add(Events(GameID=GID,EventType="StartState",PhaseData=currentGame.GamePhase,StateData=state)) 	#add an event to start the current phase
		currentGame.GameState=state	#update teh current game phase
		session.commit()



def endPhase(GID,gameover):
	'''
		ends the current phase and cycles to the next phase
		if gameover==true, does not cycle to the next phase
	'''
	with Session() as session:
		currentGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		session.add(Events(GameID=GID,EventType="EndPhase",PhaseData=currentGame.GamePhase))
		
		#if we are ending the game, we don't want to call "startPhase"
		if gameover:
			active=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).all()
			if len(active)>0:
				
				#check tos ee if we need to 'unpause'
				lastPause=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause").order_by(Events.EventID.desc())).all()
				if len(lastPause)>0:
					if lastPause[0].MiscData==1:
						session.add(Events(GameID=GID,EventType="Pause",MiscData=0))
				active[0].Active=0
				#check to see if we need to end teh active player's turn
				turns=session.scalars(select(Events).where(Events.FactionName==active[0].FactionName,or_(Events.EventType=="StartTurn",Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID)).all()
				if turns[len(turns)-1].EventType=="StartTurn":
					session.scalars(select(Factions).where(Factions.FactionName==active[0].FactionName)).first().Pass=True
					session.add(Events(GameID=GID,EventType="PassTurn",FactionName=active[0].FactionName))
			currentGame.GamePhase="Completed"
		session.commit()
	
	if not gameover:
		startPhase(GID)

def startTurn(GID,faction):
	'''
	starts a faction's turn
	create an event for turn start
	update the active faction
	'''
	with Session() as session:
		actFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==faction)).first()
		actFact.Active=True
		session.add(Events(GameID=GID,EventType="StartTurn",FactionName=actFact.FactionName))
		session.commit()
	
def endTurn(GID,faction,fPass):
	'''
	
	ends a faction's turn, if it's a pass(1), updates passing
	start's the next faction's turn
	
	create the end/pass event
	update pass status
	ID next faction
	update total time
	call startTurn or, if all pass, end phase
	'''
	passing=["EndTurn","PassTurn"]
	print(f'{faction} is {passing[fPass]}')
	with Session() as session:
		session.add(Events(GameID=GID,EventType=passing[fPass],FactionName=faction))	#create the event
		if fPass:
			print(f'Updating {faction} status to passing')
			#session.scalars(select(Factions).where(Factions.FactionName==faction)).first().Pass=True
			session.execute(update(Factions).where(Factions.FactionName==faction).values(Pass=True))
		#find the next faction
		session.commit()
	updateTime(GID,faction)	#updates total time with most recent turn
	nextFaction=findNext(GID)
	
	
	if nextFaction=="none":
		#print("Ending phase due to no players left")
		endPhase(GID,False)
	else:
		startTurn(GID,nextFaction)

def undo_endTurn(GID,faction,fPass):
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
	#this is called when the "next" faction is up, we need to go back a faction to find the correct one
	#find the previous faction
	previousFaction=findNext(GID,-1)
	#update the total time to no longer reflect our turn
	updateTime(GID,faction,-1)	
	passing=["EndTurn","PassTurn"]
	with Session() as session:
		#create the event marking a turn correction ("CorrectTurn")
		session.add(Events(GameID=GID,EventType="CorrectTurn",FactionName=faction))	
		#if we're undoing a pass, update the pass status of the player that passed
		if fPass:
			print(f'Updating {faction} status to not passing')
			#session.scalars(select(Factions).where(Factions.FactionName==faction)).first().Pass=True
			session.execute(update(Factions).where(Factions.FactionName==faction).values(Pass=False))
		#modify the "active faction" start event
		#faction is the active faction's name
		session.execute(update(Events).where(Factions.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventTime).first().values(EventType="Correct-StartTurn"))
		#modify the "previous faction" end event
		session.execute(update(Events).where(Factions.FactionName==previousFaction,Events.EventType==passing[fPass]).order_by(Events.EventTime).first().values(EventType="Correct-"+passing[fPass]))
			
		session.commit()

	#delete the previous pass or endturn
	

	
	print(previousFaction.FactionName)
	startTurn(GID,previousFaction)

def getPauseTime(GID,turnStartTime):
	'''
	finds the length of a pause
	finds all pauses with this faction
	finds all the pauses that occured since turnStart
	finds all the associated un-pauses
	calculates the time
	returns that value
	'''
	pauseTime=dt.timedelta(0)
	with Session() as session:
		#find all pauses since this turn start
		print("Start time: %s"%turnStartTime)
		pauses=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause").filter(Events.EventTime>=turnStartTime).order_by(Events.EventID.desc())).all()
		#verify we paused at least 1 time
		if len(pauses)>0:
			#for each pair of pauses, fidn teh total time paused
			for i in range(int(len(pauses)/2)):
				#find the difference 
				pauseTime+=(pauses[i*2].EventTime-pauses[(i*2)+1].EventTime)

	return pauseTime
	
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
		
		turnStart=session.scalars(select(Events).where(Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	#most recent start
		turnStop=session.scalars(select(Events).where(Events.GameID==GID,or_(Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID.desc())).first() #most recent stop
		turnTime=turnStop.EventTime-turnStart.EventTime
		
		#subtract out any pauses/combats
		turnTime-=getPauseTime(GID,turnStart.EventTime)
		print("%s turn time: %s"%(faction,turnTime))
		#find the faction we're doing the time modification for
		actFact=session.scalars(select(Factions).where(Factions.FactionName==faction)).first()
		
		#determine if this is a normal time add or if we're undoing a turn
		session.execute(update(Factions).where(Factions.FactionName==faction).values(TotalTime=actFact.TotalTime+(fwd_bwd*turnTime)))
		#if undo:
			#actFact.TotalTime-=turnTime
		#else:
			#normal add
			#actFact.TotalTime+=turnTime
		print(f'{actFact.FactionName} adding {turnTime} to total time {actFact.TotalTime}')
		session.commit()
		

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
		print([faction.FactionName for faction in activeFactions])
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
			print(f'Next faction: {nextFaction}')
			#undo the current active faction
			currentFaction.Active=False
			#assign the identified faction as active
			activeFactions[nextIndex].Active=True
			session.commit()
			return nextFaction
			
def createFactions(GID):
	#modify when adding create factions for a game (deprecate)
	with Session() as session:
		for key in UF_Dict.keys():
			session.add(Factions(FactionName=UF_Dict[key][0], 
			UserID=session.scalars(select(Users).where(Users.UserName==key)).first().UserID, 
			GameID=GID,TableOrder=UF_Dict[key][1]))
		session.commit()

def add_factions(GID, gameConfig):
	'''
		adds users/factions to the game
		gameConfig=('faction':(userID,tableOrder))
	'''
	with Session() as session:
		for item in gameConfig:
			session.add(Factions(FactionName=item[0],
			UserID=item[1][0],
			GameID=GID,
			TableOrder=item[1][1]))
		session.commit()

def create_player(pName):
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
	
		

def create_new_game(gameDate=gdate):
	'''
	creates a new game with a default date of today
	returns the newly created gameID
	'''
	print("TeSt")
	with Session() as session:
		newGame=Games(GameDate=gameDate)
		session.add(newGame)
		session.commit()
		print ("GameID {}".format(newGame.GameID))
	return newGame.GameID

def delete_old_game(GID):
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
		
def gameStat(GID):
	'''
	displays the basic game stats such as time spent in each phase, number of rounds, etc
	'''
	with Session() as session:
		pass

def getRound(GID):
	'''
	returns the round of the current game
	'''
	return Session().scalars(select(Games).where(Games.GameID==GID)).first()


#####################helper functions for initial testing####################
def turnHelper(GID,passer):
	with Session() as session:
		activeFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first().FactionName
		sleep(1)
		endTurn(GID,activeFact,passer)

		
def createNewUser(GID,uName):
	'''creates a new user and adds to db'''
	with Session() as session:
		session.add(Users(Username=uName))
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
		


def initiativeEvent(GID):
	#used for starting initiatives (deprecate)
	with Session() as session:
		res=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		initiatives={}
		i=0
		for row in res:
			i=i+1
			initiatives[row.FactionName]=i
			session.add(Events(GameID=GID,FactionName=row.FactionName,
				EventType="Initiative",MiscData=i))
			session.commit()
		updateInitiative(GID,initiatives)

def restart():
	#clears the existing DB and creates the new one
	clearAll()
	createNew()

def new_game(GID):
	#creates a new game for our use
	createGame()
	#GID=Session().scalars(select(Games).where(Games.GameDate==gdate)).first().GameID
	createUsers()
	createFactions(GID)
	
	

if __name__=="__main__":
	if len(sys.argv)>1:
		safemode=sys.argv[1]
	else:
		safemode="fuck you"
	#just a little helper function
	if safemode=="off":
		restart()
		print("restart complete")
		new_game(1)
		print("new Game created")
		#initiativeEvent(1)
		#gameStart(1)
		#endPhase(1,0)
		#endPhase(1,0)
		
		
	else:
		print("safe mode enabled")

	

	'''
	initiativeEvent(GID)
	print("setting initiative")
	pauseEvent(True,GID)
	print("Pause")
	pauseEvent(False,GID)
	print("UnPause")
	newSpeaker(UF_Dict["Charlie"][0], GID)
	print("new Speaker")
	newSpeaker(UF_Dict["Sunny"][0],GID)
	print("new Speaker")
	adjustPoints(UF_Dict["Sunny"][0],2,GID)
	print("adjust points up")
	adjustPoints(UF_Dict["Sunny"][0],-1,GID)
	print("adjust points down")
	adjustPoints(UF_Dict["Nathan"][0],1,GID)
	print("adjust points ")
	endPhase(GID,0)
	print("cycle phase 1")
	print("Starting turns")
	for i in range(0,10):
		turnHelper(GID,0)
		print("Ending turn %s at %s"%(i,dt.datetime.now()))

	print("StartingPasses")
	for i in range(0,6):
		turnHelper(GID,1)
		print("passing turn %s"%i)

	endPhase(GID,0)
	print("cycle phase 2")
	endPhase(GID,0)
	print("cycle phase 3")
	endPhase(GID,0)
	print("cycle phase 4")
	endPhase(GID,0)
	print("cycle phase 5")
	endPhase(GID,0)
	print("cycle phase 6")
	endPhase(GID,0)
	print("cycle phase 7")
	endPhase(GID,0)
	print("cycle phase 8")
	gameStop(GID)
	print("Game Over")
	'''

