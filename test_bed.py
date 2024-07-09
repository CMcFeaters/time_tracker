#used for testing the tables and various functions prior to putting it in the page
from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import datetime as dt
import bisect

gdate=dt.date.today().strftime("%Y%m%d")
UF_Dict={"Hythem":("Yssaril Tribes",2),"Charlie":("VuilRaith Cabal",1), "GRRN":("Nekro Virus",4), "Jakers":("Council Keleres",3),
		"Sunny":("Barony of Letnev",6),"Nathan":("Naaz-Rohka Alliance",5)}
Session=sessionmaker(engine)
GID=1	#value used to identify current cgame

def createGame():
	with Session()as session:
		newGame=Games(GameDate=gdate)
		session.add(newGame)
		session.commit()
		

def createUsers():
	with Session() as session:
		session.add(Users(UserName="Charlie"))
		session.add(Users(UserName="Nathan"))
		session.add(Users(UserName="Sunny"))
		session.add(Users(UserName="GRRN"))
		session.add(Users(UserName="Jakers"))
		session.add(Users(UserName="Hythem"))
		session.commit()
		
def createFactions(GID):
	with Session() as session:
		for key in UF_Dict.keys():
			session.add(Factions(FactionName=UF_Dict[key][0], 
			UserID=session.scalars(select(Users).where(Users.UserName==key)).first().UserID, 
			GameID=GID,TableOrder=UF_Dict[key][1]))
		session.commit()

def initiativeEvent(GID):
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
		updateInitiative(initiatives,GID)

def updateInitiative(initiative,GID):
	'''
	takes in a dict of initiatives in order of {"faction name":"initiative"} and updates
	can do single or batch
	'''
	with Session() as session:		
		for key in initiative:
			session.scalars(select(Factions).
			where(Factions.FactionName==key,Factions.GameID==GID)).first().Initiative=initiative[key]
		session.commit()

def pauseEvent(pup,GID):
	'''
	initiates a pause event with the state of bool pup
	'''
	with Session() as session:
		session.add(Events(GameID=GID, EventType="Pause", MiscData=pup))
		session.commit()

def newSpeaker(faction,GID):
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
		
def adjustPoints(faction,points,GID):
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
		session.commit()
	#move into the strat phase
	startPhase(GID)
		
def gameStop(GID):
	'''
	ends the game by creating a stop game event
	'''
	endPhase(GID,True)
	with Session() as session:
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
	#updateTime(faction)	#updates total time with most recent turn
	
	if nextFaction=="none":
		#print("Ending phase due to no players left")
		endPhase(GID,False)
	else:
		startTurn(GID,nextFaction)

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
			nextIndex=bisect.bisect_left(activeInitiatives,currentFaction.Initiative)%len(activeInitiatives)
			#nextIndex=(activeInitiatives.index(currentFaction.Initiative)+1)%len(activeInitiatives)
			nextFaction=activeFactions[nextIndex].FactionName #get teh name to return
			currentFaction.Active=False
			activeFactions[nextIndex].Active=True
			session.commit()
			return nextFaction
			
			
			#clear and update actives
def updateTime(GID,faction):
	'''
	given a faction and GAME ID, find the length of time of the most recent turn
	requires a closed end to turn, let's assume this is true for now
	'''
	pass
	
#start adding functionality
#port over to flask front end

def turnHelper(GID,passer):
	with Session() as session:
		activeFact=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==True)).first().FactionName
		endTurn(GID,activeFact,passer)

def restart(GID):
	createNew()
	createGame()
	#GID=Session().scalars(select(Games).where(Games.GameDate==gdate)).first().GameID
	createUsers()
	createFactions(GID)

restart(GID)
print("restart complete")
gameStart(GID)
print("Game Start complete")
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
	print("Ending turn %s"%i)

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

