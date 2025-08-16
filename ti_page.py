from flask import Flask, render_template, redirect, url_for,request
import server_api
from sqlalchemy import select, and_
from TI_TimeTracker_DB_api import Games, Users, Factions, Events, Combats
import datetime

#config=dotenv_values(".env")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
#app.config["SQLALCHEMY_DATABSE_URI"]="mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db'])

strategyNameDict={1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial",9:"None"}
 
@app.route("/")
def phase_selector():
	#this reads the current game phase and redirects the user to the representative page
		
		GID=get_active_game() #get teh active game ID or return to the welcome page
		if GID=="no_active":
			return redirect(url_for('welcome_page'))
		with server_api.Session() as session:
			print("ActiveID: %s"%GID)
			state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
			phase=session.scalars(select(Games.GamePhase).where(Games.GameID==GID)).first()
			#do all the below state stuff
			if state=="Active":
				if phase=="Setup":
					return redirect(url_for('setup_phase'))	#url for setup
				elif phase=="Action":
					return redirect(url_for('action_phase'))
				elif phase=="Status":
					return redirect(url_for('status_phase'))
				elif phase=="Agenda":
					return redirect(url_for('agenda_phase'))
				elif phase=="Strategy":
					return redirect(url_for('strategy_phase'))
				elif phase=="Completed":
					return redirect(url_for('game_winner'))	#url for end screen
				else:
					print ("Action Fuck UP")
					return redirect(url_for('error_phase'))
			elif state=="Pause":
				return redirect(url_for('game_pause'))
			elif state=="Strategic":
				return redirect(url_for('strategic_action'))
			#remove combat
			#elif state=="Combat":
			#	return redirect(url_for('game_combat'))
			else:
				print ("State fuckup: %s"%state)
				return redirect(url_for('error_phase'))


@app.route('/welcome', methods=['GET','POST'])
def welcome_page():
	'''
	this page displays a welcome screen for users allowing them to select an active game
	future options: 
		
		view stats, or create a game
		-view game stats
		-view all time stats
		-view faction stats
		-view player stats
		Show recent 10 games with view option
		Show recent 10 players with view option
		Create new game option
		Create new player option	
	'''

	with server_api.Session() as session:
		games=session.scalars(select(Games).order_by(Games.GameID)).all()
		if request.method=="POST":
			
			gameID=int(request.form['gameSelect'])
			activeGame=session.scalars(select(Games).where(Games.GameID==gameID)).first()
			activeGame.Active=1
			session.commit()
			return phase_selector()
		return render_template("welcome.html",games=games,cPhase="Welcome")

@app.route("/create_game_page", methods=['GET','POST'])
def create_game():
	'''
	this is called when a user selects the option to create a new game
	'''
	
	if request.method=='POST':
		

		#validate entries
		players=[]
		factions=[]
		for entry in range(1,9):
			'''
			go through each form row.  if it's user name is NA skip it
			if the user is already in the list return with an error
			it the faction is already in the list, return iwht an error
			else append to our two arrays
			'''
			player=request.form.get("user"+str(entry))
			faction=request.form.get("faction"+str(entry))
			if player!="NA":
				if players.count(player)==0:
					players.append(request.form.get("user"+str(entry)))
				else:
					print(f'{player} has multiple entries')
					return(redirect(url_for('create_game')))
				if factions.count(faction)==0:
					factions.append(request.form.get("faction"+str(entry)))
				else:
					print(f'{faction} has multiple entries')
					return(redirect(url_for('create_game')))
		#get the player IDS from teh player names
		playerIDs=[server_api.Session().scalars(select(Users.UserID).where(Users.UserName==player)).first() for player in players]
		#print(players)
		#print(playerIDs)
		#put it all into a single array of tuples (userID,(faction,order))
		gameConfig=[(factions[i],(playerIDs[i],i+1)) for i in range(len(players))]
		#print(gameConfig)
		#create the game
		gID=server_api.createNewGame()
		#print(f'game created')
		#add factions tot he game
		server_api.addFactions(gID,gameConfig)
		server_api.newSpeaker(gID,factions[0])
		#print(f'factions added')
		return redirect(url_for('welcome_page'))

	else:
		with server_api.Session() as session:
			players=session.scalars(select(Users.UserName)).all()
			players.append('NA')
			faction_choices=['Arborec','Argent Flight','Barony of Letnev','Clan of Saar','Council Keleres','Embers of Muaat','Emirates of Hacan','Empyrean','Federation of Sol',
			'Ghosts of Creuss','L1Z1X Mindnet','Mahact Gene-Sorcerers','Mentak Coalition','Naalu Collective','Naaz-Rokha Alliance','Nekro Virus','Nomad','Sardakk N’orr',
			'Titans of Ul','Universities of Jol-Nar','Vuil Raith Cabal','Winnu','Xxcha Kingdom','Yin Brotherhood','Yssaril Tribes']
		return render_template("create_game.html",players=players,faction_choices=faction_choices,cPhase="Welcome")

@app.route("/add_player_page",methods=['GET','POST'])
def add_player():
	'''
		create a new player, reads data from text box
		need to do input validation
	'''
	if request.method=="POST":
		player=request.form.get("pName")
		server_api.createPlayer(player)
		return redirect(url_for('welcome_page'))
	
	return render_template('add_player.html',cPhase="Welcome")

@app.route("/delete_game_page", methods=['GET','POST'])
def delete_game():
	'''
	this is called when a user selects the option to create a new game
	'''
	
	
	if request.method=='POST':
		print("HERE WE ARE")
		#this will be what we do when we create a new game
		dGID=request.form.get("deleteGame")	#validate entries
		if request.form.get(dGID)=="NO":
			#if they didn't select "YES" return to the welcome page
			print(f'{dGID} - No selected')
		else:
			#else we are deleting it	
			print(f'We are deleting game: {dGID}')
			server_api.deleteOldGame(int(dGID))
		return redirect(url_for('welcome_page'))
	with server_api.Session() as session:
		games=session.scalars(select(Games).order_by(Games.GameID)).all()
	return render_template("delete.html",games=games,cPhase="Welcome")

	
@app.route('/setup', methods=['GET','POST'])
def setup_phase():
	'''
	this page is for whena game is created but hasn't started
	users have the option to start the game go back to teh welcome screen
	'''
	GID=get_active_game()	#get teh active game
	with server_api.Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()	#get all teh factions for the bottom element
		if request.method=="POST":	#if they hit the "Start button"
			
			server_api.endPhase(GID,0) #end the setup phase
			return phase_selector()
		return render_template("setup_phase.html",factions=factions,cPhase="Setup", flavor="Phase")
		
@app.route('/viewGame')
def viewGame_page(GID):
	'''
	a page where users view the status of a single game
	this will pump out all the relevant stats we want to see
	'''
	GID=get_active_game() #get teh acftive game ID or return to the welcome page
	pass

@app.route('/pause', methods=['GET','POST'])
def game_pause():
	#pause page, underlying code creates a pause event
	#page allows users to unpause or go through the end-game cycle
	'''
		NOTE: may want to add a "pause" state somewhere in the db  rather than just having it as
		an event so that it has some resiliency 
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	with server_api.Session() as session:
		#get the state
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
	
	#check if the unpause button was pressed
	'''
	IS THERE A REASON WE USE 0/1 instead of PAUSE and UNPAUSE events.
	If we want to change this we'll have to also address the "time tracking" function
	'''
	if request.method=="POST":
		server_api.boolEvent(GID,"Pause",0)	#create an event the phase ended
		server_api.changeState(GID,"Active")		#change the state back to action phase
		return phase_selector()
	else:
		#we can only enter the pause state from the action state
		#otherwise go back to our current state
		if state=="Active":  #first time we're here
			server_api.boolEvent(GID,"Pause",1) 	#add the pause event
			server_api.changeState(GID,"Pause")	#change the state
		#remove option for combat state
		#elif state=="Combat":	#we clicked puase while in combat, go to combat
		#	return redirect(url_for('game_combat'))
		elif state=="Strategic":	#we clicked puase while in strategic action, go to combat
			return redirect(url_for('strategic_action'))
		return render_template("pause.html", cPhase="Paused", factions=factions, flavor="Game")	#if the state is pause or active, go to pause page

# remove COMBAT PAGE
'''
@app.route('/combat', methods=['GET','POST'])
def game_combat():
	#pause page, underlying code creates a pause event
	#page allows users to unpause or go through the end-game cycle
	
		#NOTE: may want to add a "combat" state somewhere in the db  rather than just having it as
		#an event so that it has some resiliency 
	#will have to initiate combat event (Default start/stop time will be "now")
	#will have to stop combat event (need ot change devault stop time to "now")
	
	GID=get_active_game() #get teh active game ID or return to the welcome page
	with server_api.Session() as session:	#get state and factions 
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
	
	
	#if we are posting to this page, we are either aborting combat (draw/misclick) or completing combat
	#this determines what type of event we create and if we make an entry
	#in the combat table
	
	if request.method=="POST":
		activeCombat=session.scalars(select(Combats).where(and_(Games.GameID==GID,Combats.Active==1))).first()
		if (request.form.get('action')):	#check if one of our action buttons was pressed
			
			#the active combat is over, determine if we update participants or call it a draw
			
			
			if(request.form['action']=="complete"):	#check if it was completed
				print("combat completed")
				#combat table entry
				activeCombat.Aggressor=request.form['Aggressor']
				activeCombat.Defender=request.form.get('Defender')
				if request.form.get('winner')=="aggressor":
					activeCombat.Winner=request.form.get('Aggressor')
				elif request.form.get('winner')=="defender":
					activeCombat.Winner=request.form.get('Aggressor')
					
			activeCombat.Active=0		#end the combat active status
			activeCombat.StopTime=datetime.datetime.now()
			session.commit()
			server_api.boolEvent(GID,"Combat",0)	#combat endevent
			server_api.changeState(GID,"Active")	#Update teh game state
		return phase_selector()	#find our true page
	else:
		if state=="Active":	#combat can only be entered from active, otherwise we ignore
			
			#	create a new combat event, chagne stte to combat and create an entry in our
			#	combat table
			
			server_api.boolEvent(GID,"Combat",1)	#update event
			server_api.changeState(GID,"Combat")	#update state
			server_api.Session.add(Combats(GameID=GID))	#create a new combat event
			session.commit()
		elif state=="Pause":	#we hit combat  while in pause
			return redirect(url_for('game_pause'))	#return to pause page
		return render_template("combat.html", cPhase="Glorious", factions=factions, flavor="Combat")	#go to the combat page (active/combat) state

'''

@app.route('/stop', methods=['GET'])
def stop_game():
	'''
		This deactivates the current game and kicks you to the phase_select screen
	'''
	GID=get_active_game()
	with server_api.Session() as session:
		activeGame=session.scalars(select(Games).where(Games.GameID==GID)).first()
		activeGame.Active=0
		session.commit()
	return phase_selector()

@app.route('/end', methods=['GET','POST'])
def end_game():
	'''
		this page allows teh user to select the game being over
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=='POST':
		print("here")
		server_api.gameStop(GID,request.form.get('winner'))
		return phase_selector()
	else:
		with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(and_(Factions.Score,Factions.TotalTime))).all()
			return render_template("end_game.html",factions=factions, cPhase="End", flavor="It?")
		
@app.route('/winner', methods=['GET','POST'])
def game_winner():
	'''
	this is the page you get when the game is oVER!
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	with server_api.Session() as session:
		winner=session.scalars(select(Games).where(Games.GameID==GID)).first()
		winningFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		uID=session.scalars(select(Factions.UserID).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		factions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName!=winner.GameWinner).order_by(and_(Factions.Score,Factions.TotalTime))).all()
		user=session.scalars(select(Users).where(Users.UserID==uID)).first()
		return render_template('winner.html',winningFaction=winningFaction, user=user, factions=factions, cPhase="Gratz",flavor="Nerd")	#create this item

@app.route("/Error")
def error_phase():
	'''
	default error page for when somethign goes wrong
	'''
	with server_api.Session() as session:
		users=session.scalars(select(Users)).all()
		#factions=session.scalars(select(Faction
		return render_template("show_users.html",users=users)


@app.route("/footer_update", methods=['POST'])
def footer_update():
	'''
	this function is called when one of the buttons in the footer is pressed
	it updates speaker, or score, then redirects to the appropriate URL function
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=='POST':
		with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
			'''this section checks through the from results to determine if a button
			was pressed related to a specific faction such as make speaker, +/- point
			'''
			for faction in factions:
				if request.form.get(faction.FactionName):
					if request.form[faction.FactionName]=="speaker":
						#select a new speaker
						server_api.newSpeaker(GID,faction.FactionName)
					
					elif(request.form[faction.FactionName]=="score"):
						#add a point
						server_api.adjustPoints(GID,faction.FactionName,1)
					if(request.form[faction.FactionName]=="correct"):
						#remove a point
						server_api.adjustPoints(GID,faction.FactionName,-1)
	return phase_selector()

@app.route("/action", methods=['GET','POST'])#here get/post
def action_phase():
	'''
	action phase page allowing you to end/pass turns,
	display turn order
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=='POST':

		with server_api.Session() as session:
			'''
			end/pass active factions turn
			'''
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
			#figure out what we're doing and execute that
			if(request.form.get('action')):
				if(request.form['action']=="end"):
					if (request.form.get('combat')):
						print(f"Combat: {request.form['combat']} detected")
						server_api.endTurn(GID,activeFaction.FactionName,0,3)
					else:
						print(f"No combat detected {request.form.get('combat')}")
						server_api.endTurn(GID,activeFaction.FactionName,0)
				elif(request.form['action']=="pass"):
					server_api.endTurn(GID,activeFaction.FactionName,1)
					return(phase_selector())	#on everyone passing we will go to the next phase
				elif(request.form['action']=="undo"):
					print(f'*******************Undoing turn for {activeFaction.FactionName}')
					server_api.undoEndTurn(GID,activeFaction.FactionName)
					return(phase_selector())
					#print(f'Complete')
				elif(request.form['action']=="Strategy1"):
					print("strategy 1 pressed")
					server_api.changeStateStrat(GID,"Strategic",activeFaction.Strategy1)
					return(phase_selector())
					#return redirect(url_for("strategic_action",strategy="1"))	#on everyone passing we will go to the next phase
				elif(request.form['action']=="Strategy2"):
					print("strategy 2 pressed")
					server_api.changeStateStrat(GID,"Strategic",activeFaction.Strategy2)
					return(phase_selector())
					#return redirect(url_for("strategic_action",strategy="2"))	#on everyone passing we will go to the next phase

	with server_api.Session() as session:
		'''find the next faction or list none if there is no next'''
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
		activeUser=session.scalars(select(Users).where(Users.UserID==activeFaction.UserID)).first().UserName
		nextFaction=""
		i=1
		while nextFaction=="":	
			tNext=factions[(factions.index(activeFaction)+i)%len(factions)]
			if tNext.Pass==False:
				#print("Status of %s: %s"%(tNext.FactionName,tNext.Pass))
				nextFaction=tNext
			else:
				i+=1
			if i>len(factions):
				nextFaction="None"
		#for faction in factions:
			#print(f'{faction.FactionName} total time: {faction.TotalTime}')
			
	return render_template("action_phase.html",factions=factions, activeUser=activeUser,activeFaction=activeFaction, nextFaction=nextFaction, cPhase="Action", flavor="Phase")
		

@app.route("/agenda", methods=['GET','POST'])
def agenda_phase():
	#manage agenda phase
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=='POST':
		with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.TableOrder)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					server_api.adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
			if request.form.get('action'):
				server_api.endPhase(GID,0)
				return phase_selector()
	
	with server_api.Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		sFactions=server_api.getSpeakerOrder(GID)
	return render_template("agenda_phase.html",factions=factions,sFactions=sFactions,cPhase="Agenda", flavor="Phase")


@app.route("/status", methods=['GET','POST'])#here get/post
def status_phase():
	'''
		this page displays the steps for the status phase and allows you to move to the next phase
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=='POST':
		'''with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					server_api.adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
		'''
		if request.form.get('action'):
			server_api.endPhase(GID,0)
			return phase_selector()

	with server_api.Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		
	return render_template("status_phase.html",factions=factions,cPhase="Status",flavor="Phase")


@app.route("/strategicAction", methods=['GET','POST'])
def strategic_action():
	'''
		this page allows the user to select initiatives
		must select different initiatives for each faction
		need something to bounce you out of here if you're in the wrong state
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=="POST":
		if request.form['action']=='undo':
			print(f'Undo Pressed: STRAT')
			server_api.undoEndStrat(GID)
			return redirect(url_for('phase_selector'))
		#identify who just finished:
		#create finished event for whoever just finished
		#find who's next 
		#check if they are the activefaction (e.g., we looped)
		#if no:
			#startstrat for next
			#reload page with them as next
		#if yes:
			#change to state to active
			#find next faction
			#start turn next faction
			#update Strat Status
			#return to phase selector
		currentFactionName=server_api.findActiveStrat(GID)	#identify whos next, should give us the end-find next sequence
		server_api.endStrat(GID,currentFactionName)	#create end event
		nextFaction=server_api.findActiveStrat(GID)	#identify whos next, should give us the end-find next sequence
		
		if nextFaction==server_api.Session().scalars(select(Factions).where(Factions.GameID==GID,Factions.Active==1)).first().FactionName:	#if the next faction is the currently active faction, we're done
			'''
				this current has 3 updates done at different phases.  all of these updates need to execute and should be atomic (they all work or they don't coccur)
				to preserve the state of the system
			'''
			server_api.closeStrat(GID)	#update the strat card status to 0 (done)
			nextFaction=server_api.findNext(GID)	#find the next faction
			server_api.startTurn(GID,nextFaction)	#set the next faction as active, and initiate a start turn event
			server_api.changeState(GID,"Active")	#update the state, we're done with strategic
			return(phase_selector())	#phase select next section
		else:	#move on to the next faction
			server_api.startStrat(GID,nextFaction)
	
	#if we are "get" it's the first time we're in the session, the action is to the active player to complete their s
	#strategic action.
	#here we find teh active player, load up the screen with stratFaction as activeFaction
	with server_api.Session() as session:
		#get the old faction
		factions=server_api.getFactions(GID)
		strategy=server_api.findStrat(GID)[1]	#identify the strategy we're using

		sFactions=server_api.getSpeakerOrder(GID,True)	#line up the factions in the correct order
		activeFaction=server_api.findActiveStrat(GID)	#find out who's up
		#print(f'Active Faction: {activeFaction} for game {GID}')
		return render_template("strategic_action.html", factions=factions,sFactions=sFactions, stratFaction=activeFaction,cPhase=strategy)

@app.route("/strategy", methods=['GET','POST'])
def strategy_phase():
	'''
		this page allows the user to select initiatives
		must select different initiatives for each faction
	'''
	GID=get_active_game() #get teh active game ID or return to the welcome page
	if request.method=="POST":
		#here is where we'd check the initiatives, assign them, jump to action phase
		initDict={}	#create a dict to store our strats in {faction:(strat1,strat2)}
		with server_api.Session() as session:
			factions=session.scalars(select(Factions.FactionName).where(Factions.GameID==GID)).all()	#get all factions
			inits=[request.form.get(faction) for faction in factions]	#get inits (assuming 1 strat)
			factions2=[faction+"2" for faction in factions]	#get factions list to access second set of strats stored in {faction}"2"
			if len(factions)<5:
				#if we are picking two strats, add the second set of strat selections
				[inits.append(request.form.get(faction)) for faction in factions2]	#append second strat to inits
				for faction in factions:
					initDict[faction]=(int(request.form.get(faction)),int(request.form.get(faction+'2')))	#add second strat to our init dict
			else:
				for faction in factions:
					initDict[faction]=(int(request.form.get(faction)),9)	#else, add 9s to our init dict to represent garbage
					
			#check to see if the same init is picked multiple times
			for init in inits:
				if inits.count(init)>1:
					print("Initiative %s selected multiple times"%request.form.get(faction))
					return redirect(url_for("strategy_phase"))
			
		server_api.assignStrat(GID,initDict)	#update initiatives
		server_api.endPhase(GID,0)	#update phase
		return phase_selector() #move to action phase
	else:
		with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			sFactions=server_api.getSpeakerOrder(GID)
			initiatives=range(1,9)
			return render_template("strategy_phase.html",factions=factions, nFactions=len(factions),sFactions=sFactions, initiatives=initiatives, cPhase="Strategy", flavor="Phase")

def get_active_game():
	'''
		gets the active game or cleansup the games if multiple active
		if active game returns ID
		if multipe or 0 active, sets no active games and redirects to welcome page
	'''
	
	with server_api.Session() as session:
		activeGames=session.scalars(select(Games).where(Games.Active==1)).all()
		if len(activeGames)>1:
			#multiple active games detected.  close them all and revert them back to the menu
			for game in activeGames:
				game.Active=0
			session.commit()
			print("Multiple Games")
			return "no_active"
		elif len(activeGames)==0:
			#no active games
			print("No Games")
			return "no_active"
		else:
			#return just the active game
			#print("Active Game: %s"%activeGames[0].GameID)
			return activeGames[0].GameID
			
