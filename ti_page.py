from flask import Flask, render_template, redirect, url_for,request
import server_api
from sqlalchemy import select, and_
from TI_TimeTracker_DB_api import Games, Users, Factions, Events, Turns
import datetime

#config=dotenv_values(".env")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
#app.config["SQLALCHEMY_DATABSE_URI"]="mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db'])

strategyNameDict={1:"Leadership",2:"Diplomacy",3:"Politics",4:"Construction",5:"Trade",6:"Warfare",7:"Technology",8:"Imperial",9:"None"}
 
@app.route("/")
def phase_selector():
	#this reads the current game phase and redirects the user to the representative page
		
		gameBase=server_api.getActiveGame()
		if gameBase is None:
			print('no activ games')
			return redirect(url_for('welcome_page'))
		GID=gameBase.GameID


		state=gameBase.GameState
		phase=gameBase.GamePhase
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


	games=server_api.getRawData()['games']
	if request.method=="POST":
		GID=int(request.form['gameSelect'])
		print(f'GID: {GID}')
		server_api.activateGame(GID)
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
			results in an array of players and an array of factions
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
		#get the list of user objects
		users=server_api.getRawData()['users']
		#generate a list of userids for the  names in players
		playerIDs=[user.UserID  for user in users  for player in players if user.UserName==player]
		#get the player IDS from teh player names
		#playerIDs=[server_api.Session().scalars(select(Users.UserID).where(Users.UserName==player)).first() for player in players]
		#print(players)
		#print(playerIDs)
		#put it all into a single array of tuples (faction,(userID,order))
		gameConfig=[(factions[i],(playerIDs[i],i+1)) for i in range(len(players))]
		print(gameConfig)
		#this shoudl be a single function
		#create the game
		server_api.createNewGame(gameConfig)
		#print(f'game created')
		#add factions tot he game
		
		#print(f'factions added')
		return redirect(url_for('welcome_page'))

	else:
		players=[user.UserName for user in server_api.getRawData()['users']]
		players.append('NA')
		faction_choices=['Arborec','Argent Flight','Barony of Letnev','Clan of Saar','Council Keleres','Crimson Rebellion','Deepwrought Scholarate','Embers of Muaat','Emirates of Hacan','Empyrean','Federation of Sol',
		'Firmament-Obsidian','Ghosts of Creuss','Last Bastion','L1Z1X Mindnet','Mahact Gene-Sorcerers','Mentak Coalition','Naalu Collective','Naaz-Rokha Alliance','Nekro Virus','Nomad','Sardakk N’orr',
		'Ral Nel Consortium','Titans of Ul','Universities of Jol-Nar','Vuil Raith Cabal','Winnu','Xxcha Kingdom','Yin Brotherhood','Yssaril Tribes']
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
	games=server_api.getRawData()['games']
	return render_template("delete.html",games=games,cPhase="Welcome")

	
@app.route('/setup', methods=['GET','POST'])
def setup_phase():
	'''
	this page is for whena game is created but hasn't started
	users have the option to start the game go back to teh welcome screen
	'''
	gameBase=server_api.getActiveGame()
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID
	
	factions=server_api.getGameData(GID)['factions']
	if request.method=="POST":	#if they hit the "Start button"
		server_api.createSetup(GID)
		return phase_selector()
	return render_template("setup_phase.html",factions=factions,cPhase="Setup", flavor="Phase")
		
@app.route('/viewGame')
def viewGame_page(GID):
	'''
	a page where users view the status of a single game
	this will pump out all the relevant stats we want to see
	'''
	gameBase=server_api.getActiveGame() #get teh acftive game ID or return to the welcome page
	pass

@app.route('/pause', methods=['GET','POST'])
def game_pause():
	#pause page, underlying code creates a pause event
	#page allows users to unpause or go through the end-game cycle
	'''
		NOTE: may want to add a "pause" state somewhere in the db  rather than just having it as
		an event so that it has some resiliency 
	'''
	#assign the game id
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID
	#get all the needed data from the server
	dataDict=server_api.getGameData(GID)
	factions=dataDict['factions']
	state=dataDict['game'].GameState
	
	#check if the unpause button was pressed
	'''
	IS THERE A REASON WE USE 0/1 instead of PAUSE and UNPAUSE events.
	If we want to change this we'll have to also address the "time tracking" function
	'''
	if request.method=="POST":
		server_api.changeState(GID,"Active")		#change the state back to action phase
		return phase_selector()
	else:
		#we can only enter the pause state from the action state
		#otherwise go back to our current state
		if state=="Active":  #first time we're here
			server_api.changeState(GID,"Pause")	#change the state
		#remove option for combat state
		#elif state=="Combat":	#we clicked puase while in combat, go to combat
		#	return redirect(url_for('game_combat'))
		elif state=="Strategic":	#we clicked puase while in strategic action, go to combat
			return redirect(url_for('strategic_action'))
		return render_template("pause.html", cPhase="Paused", factions=factions, flavor="Game")	#if the state is pause or active, go to pause page

@app.route('/stop', methods=['GET'])
def stop_game():
	'''
		This deactivates the current game and kicks you to the phase_select screen
		
	'''
	#get the game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID

	server_api.stopGame(GID)
	return phase_selector()

@app.route('/end', methods=['GET','POST'])
def end_game():
	'''
		this page allows teh user to select the game being over
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	if request.method=='POST':
		print("here")
		server_api.gameStop(GID,request.form.get('winner'))
		return phase_selector()
	else:
		
		factions=server_api.getGameData(GID)['factions']
		return render_template("end_game.html",factions=factions, cPhase="End", flavor="It?")
		
@app.route('/winner', methods=['GET','POST'])
def game_winner():
	'''
	this is the page you get when the game is oVER!
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	
	GID=gameBase.GameID

	with server_api.Session() as session:
		dataDict=server_api.getWinData(GID)
		factions=server_api.getGameData(GID)['factions']
		return render_template('winner.html',winningFaction=dataDict['wFaction'], user=dataDict['wUser'], factions=factions, cPhase="Hail the",flavor="Emporer")	#create this item

@app.route("/Error")
def error_phase():
	'''
	default error page for when somethign goes wrong
	'''
	return render_template("show_users.html")


@app.route("/footer_update", methods=['POST'])
def footer_update():
	'''
	this function is called when one of the buttons in the footer is pressed
	it updates speaker, or score, then redirects to the appropriate URL function
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	
	GID=gameBase.GameID

	if request.method=='POST':
		factions=server_api.getGameData(GID)['factions']
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
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	#gather basic info needed for this function
	GID=gameBase.GameID


	#activeFaction
	activeFaction=server_api.getGameData(GID)["activeFaction"]


	if request.method=='POST':

		if(request.form.get('action')):
			if(request.form['action']=="end"):
				if (request.form.get('combat')):
					print(f"Debug Combat: {request.form['combat']} detected")
					server_api.endTurn(GID,activeFaction.FactionName,2)
				else:
					print(f"Debug: No combat detected {request.form.get('combat')}")
					server_api.endTurn(GID,activeFaction.FactionName,0)
			elif(request.form['action']=="pass"):
				server_api.endTurn(GID,activeFaction.FactionName,1)
				return(phase_selector())	#on everyone passing we will go to the next phase
			elif(request.form['action']=="undo"):
				print(f'*******************Undoing turn for {activeFaction.FactionName}')
				server_api.undoEndTurn(GID,activeFaction.FactionName)
				return(phase_selector())
				#print(f'Complete')
			#did we press the first strategic action
			elif(request.form['action']=="Strategy1"):
				print("strategy 1 pressed")
				server_api.changeStateToStrat(GID,"Strategic",activeFaction.Strategy1,activeFaction.FactionName)
				return(phase_selector())
			#did we press a second strategic action?
			elif(request.form['action']=="Strategy2"):
				print("strategy 2 pressed")
				server_api.changeStateToStrat(GID,"Strategic",activeFaction.Strategy2,activeFaction.FactionName)
				return(phase_selector())
				#return redirect(url_for("strategic_action",strategy="2"))	#on everyone passing we will go to the next phase
	
	#grabbing the updated data
	gameDataDict=server_api.getGameData(GID)
	#list of factions
	factions=gameDataDict["factions"]
	#activeFaction
	activeFaction=gameDataDict["activeFaction"]
	#active user
	activeUser=gameDataDict['activeUser']
	
	'''
	i'm removing this feature
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
	'''		
	return render_template("action_phase.html",factions=factions, activeUser=activeUser,activeFaction=activeFaction, cPhase="Action", flavor="Phase")
		

@app.route("/agenda", methods=['GET','POST'])
def agenda_phase():
	#manage agenda phase
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	
	GID=gameBase.GameID

	if request.method=='POST':
		#these following lines are from when we used to update points here
#		with server_api.Session() as session:
#			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.TableOrder)).all()
#			for faction in factions:
#				if request.form.get(faction.FactionName):
#					server_api.adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))

		server_api.endPhase(GID,0)
		return phase_selector()
	
	
	factions=server_api.getGameData(GID)['factions']
	sFactions=server_api.getSpeakerOrder(GID)
	return render_template("agenda_phase.html",factions=factions,sFactions=sFactions,cPhase="Agenda", flavor="Phase")


@app.route("/status", methods=['GET','POST'])#here get/post
def status_phase():
	'''
		this page displays the steps for the status phase and allows you to move to the next phase
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID

	if request.method=='POST':
		'''with server_api.Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					server_api.adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
		'''
		#see if we're going to the next phase
		if request.form.get('action'):
			server_api.endPhase(GID,0)
			return phase_selector()

	#get teh factions
	factions=server_api.getGameData(GID)['factions']
		
	return render_template("status_phase.html",factions=factions,cPhase="Status",flavor="Phase")


@app.route("/strategicAction", methods=['GET','POST'])
def strategic_action():
	'''
		this page is the main page for performing strategic actions
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID
	#if it's a post, someone has hit the "done" button
	if request.method=="POST":
		#did they hit undo?
		if request.form['action']=='undo':
			print(f'Undo Pressed: STRAT')
			#do the undo magic
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
		#identify whos currently activestragety
		currentFactionName=server_api.getFactionAndStrat(GID)[0].FactionName #this will be either the start turn or the startstate
		nextFaction=server_api.findNextSpeakerOrderByName(GID,currentFactionName)
		activeFaction=server_api.getGameData(GID)['activeFaction']
		#print(f'Next Faction: {nextFaction} active Faction: {activeFaction}')
		#check to see fi we have looped back to the active(first) faction and completed all our strategic actions
		if nextFaction==activeFaction.FactionName:	#if the next faction is the currently active faction, we're done
			'''
				this current has 3 updates done at different phases.  all of these updates need to execute and should be atomic (they all work or they don't coccur)
				to preserve the state of the system, but alas, i didn't do that
			'''
			#close the strat card in factions
			#create end event and end that strategic action and update that activestrategy faction status to 0
			#server_api.endStrat(GID,currentFactionName)	
			#change closestrat to retun the strat and faction to close
			#call closestrat function to: 
			# close teh strat state, update the game strat info, update the faction strat card data, start the next factions turn
			server_api.closeStrat(GID)	#update the strat card status to 0 (done)

			#find teh faction that is supposed to be next in initiative order for the active state
			#just return th enerxt strat (already done)
			#nextFaction=server_api.findAndSetNext(GID)	#find the next faction
			#change the state back to active
			#in the larger function change this to a 
			#server_api.changeState(GID,"Active")	#update the state, we're done with strategic
			#start teh next factions turn
			#server_api.startFactTurn(GID,nextFaction)	#set the next faction as active, and initiate a start turn event
			
			#return to the phase selector to continue forward
			return(phase_selector())	#phase select next section
		else:	#move on to the next faction
			#create end event and end that strategic action and update that activestrategy faction status to 0
			#end strat/start strat should be an atomic action.
			server_api.transitionStrat(GID,currentFactionName,nextFaction)	
			#create a start event and update the active strategy status to 1 for the next faction
	
	#if we are "get" it's the first time we're in the session, the action is to the active player to complete their s
	#strategic action.
	#here we find teh active player, load up the screen with stratFaction as activeFaction

	#get the factions
	factions=server_api.getFactions(GID)
	#get thefaction and strategy that was selected
	factstrat=server_api.getFactionAndStrat(GID)
#	print(f'Debug: Faction: {factstrat[0].FactionName} Strategy: {factstrat[1]}|{factstrat[2]}')
	#get teh speakerorder of factions
	sFactions=server_api.getSpeakerOrder(GID,True)	#line up the factions in the correct order

	return render_template("strategic_action.html", factions=factions,sFactions=sFactions, stratFaction=factstrat[0],cPhase=factstrat[2])

@app.route("/strategy", methods=['GET','POST'])
def strategy_phase():
	'''
		this page allows the user to select initiatives
		must select different initiatives for each faction
	'''
	#get teh game info
	gameBase=server_api.getActiveGame()
	#if there is no active game, return to the welcome page
	if gameBase is None:
		print('no activ games')
		return redirect(url_for('welcome_page'))
	GID=gameBase.GameID
	if request.method=="POST":
		#here is where we'd check the initiatives, assign them, jump to action phase
		initDict={}	#create a dict to store our strats in {faction:(strat1,strat2)}

		factions=server_api.getGameData(GID)['factions']
		inits=[request.form.get(faction.FactionName) for faction in factions]	#get inits (assuming 1 strat)
		factions2=[faction.FactionName+"2" for faction in factions]	#get factions list to access second set of strats stored in {faction}"2"
		if len(factions)<5:
			#if we are picking two strats, add the second set of strat selections
			[inits.append(request.form.get(faction)) for faction in factions2]	#append second strat to inits
			for faction in factions:
				initDict[faction.FactionName]=(int(request.form.get(faction.FactionName)),int(request.form.get(faction.FactionName+'2')))	#add second strat to our init dict
		else:
			for faction in factions:
				initDict[faction.FactionName]=(int(request.form.get(faction.FactionName)),9)	#else, add 9s to our init dict to represent garbage
		naaluFaction=request.form.get('initiative-0')
		print(f'Naalu Faction: {naaluFaction}')
		#check to see if the same init is picked multiple times
		for init in inits:
			if inits.count(init)>1:
				print("Initiative %s selected multiple times"%init)
				return redirect(url_for("strategy_phase"))
		
		server_api.assignStrat(GID,initDict,naaluFaction)	#update initiatives
		return phase_selector() #move to action phase
	else:
		factions=server_api.getGameData(GID)['factions']
		sFactions=server_api.getSpeakerOrder(GID)
		initiatives=range(1,9)
		naalu=[faction.FactionName for faction in factions].count("Naalu Collective")
		print(f"Naalu: {naalu}")
		return render_template("strategy_phase.html",factions=factions, nFactions=len(factions),sFactions=sFactions, initiatives=initiatives, cPhase="Strategy", flavor="Phase", naalu=naalu)

			
