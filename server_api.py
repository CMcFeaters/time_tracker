'''
"backend" interface for teh server.  Includes all the functions called by the server when accessing the system
'''
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats
from sqlalchemy import select, or_
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect
from time import sleep
import sys

#modify when we create games
gdate=dt.date.today().strftime("%Y%m%d")

#delete later
UF_Dict={"Charlie":("VuilRaith Cabal",1), "GRRN":("Nekro Virus",3), "Jakers":("Council Keleres",2),
		"Sunny":("Barony of Letnev",5),"Nathan":("Naaz-Rohka Alliance",4)}
Session=sessionmaker(engine)

#modify 
#GID 1 = winner screen
#GID 2 = action phases

GID=1	#value used to identify current only during creating a enw game with script for testing



			
			

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
		session.add(Events(GameID=GID,EventType="GameStart"))
		session.add(Events(GameID=GID, EventType="StartPhase", PhaseData="Setup"))	#create the event
		session.commit()
	#move into the strat phase
	startPhase(GID)
		
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
		#create new phase
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
	ends a faction's turn, if it's a pass, updates passing
	start's the next faction's turn
	
	create the end/pass event
	update pass status
	ID next faction
	update total time
	call startTurn or, if all pass, end phase
	'''
	passing=["EndTurn","PassTurn"]
	with Session() as session:
		session.add(Events(GameID=GID,EventType=passing[fPass],FactionName=faction))	#create the event
		if fPass:
			session.scalars(select(Factions).where(Factions.FactionName==faction)).first().Pass=True
		#find the next faction
		session.commit()
	nextFaction=findNext(GID)
	updateTime(GID,faction)	#updates total time with most recent turn
	
	if nextFaction=="none":
		#print("Ending phase due to no players left")
		endPhase(GID,False)
	else:
		startTurn(GID,nextFaction)

def updateTime(GID,faction):
	'''
	finds the time delta and applies it to the factions total time
	'''
	with Session() as session:
		turnStart=session.scalars(select(Events).where(Events.FactionName==faction,Events.EventType=="StartTurn").order_by(Events.EventID.desc())).first()	#most recent start
		turnStop=session.scalars(select(Events).where(Events.FactionName==faction,Events.GameID==GID,or_(Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID.desc())).first() #most recent stop
		turnTime=turnStop.EventTime-turnStart.EventTime	#subtract the last and second to last (lazy but i'm on a fucking schedule)
		
		#find pause
		lastPause=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause",Events.MiscData==1).order_by(Events.EventID.desc())).all()
		if len(lastPause)>0:
			lastPause=lastPause[0]
			lastUnPause=session.scalars(select(Events).where(Events.GameID==GID,Events.EventType=="Pause",Events.MiscData==0).order_by(Events.EventID.desc())).first()
			if (lastPause.EventID>turnStart.EventID and lastPause.EventID<turnStop.EventID):
				#there was a pause
				pauseTime=lastUnPause.EventTime-lastPause.EventTime
				turnTime-=pauseTime
		print("%s turn time: %s"%(faction,turnTime))
		actFact=session.scalars(select(Factions).where(Factions.FactionName==faction)).first()
		actFact.TotalTime+=turnTime
		session.commit()
		

def findNext(GID):
	'''
	give the current active faction, determines the next active faction and returns the faction name.  if all factions have passed, return "none"
	
	updates the active factions 
	'''
	with Session() as session:
		activeFactions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
		if len(activeFactions)==0:	#if no one is active, clear the active faction and return "none"
			factions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first().Active=False
			session.commit()
			return "none"
		else:
			#there are some remaining unpassed factions
			activeInitiatives=session.scalars(select(Factions.Initiative).where(Factions.GameID==GID,Factions.Pass==0).order_by(Factions.Initiative)).all()
			currentFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first()
			#use current faction to find the next faction
			print(activeInitiatives)
			if activeInitiatives.count(currentFaction.Initiative)>0:
				nextIndex=(activeInitiatives.index(currentFaction.Initiative)+1)%len(activeInitiatives)
			else:
				nextIndex=bisect.bisect_left(activeInitiatives,currentFaction.Initiative)%len(activeInitiatives)
			#nextIndex=(activeInitiatives.index(currentFaction.Initiative)+1)%len(activeInitiatives)
			nextFaction=activeFactions[nextIndex].FactionName #get teh name to return
			currentFaction.Active=False
			activeFactions[nextIndex].Active=True
			session.commit()
			return nextFaction
			
			
			#clear and update actives
	
#start adding functionality
#port over to flask front end

def gameStat(GID):
	'''
	displays the basic game stats such as time spent in each phase, number of rounds, etc
	'''
	with Session() as session:
		pass
		

#####################helper functions for initial testing####################
def turnHelper(GID,passer):
	with Session() as session:
		activeFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first().FactionName
		sleep(1)
		endTurn(GID,activeFact,passer)

def createGame():
	#modify when we get to creating games
	with Session() as session:
		newGame=Games(GameDate=gdate)
		session.add(newGame)
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
		
def createFactions(GID):
	#modify when adding create factions for a game (deprecate)
	with Session() as session:
		for key in UF_Dict.keys():
			session.add(Factions(FactionName=UF_Dict[key][0], 
			UserID=session.scalars(select(Users).where(Users.UserName==key)).first().UserID, 
			GameID=GID,TableOrder=UF_Dict[key][1]))
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
		new_game(GID)
		print("new Game created")
		initiativeEvent(GID)
		gameStart(GID)
		
		
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

