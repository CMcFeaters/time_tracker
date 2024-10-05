from flask import Flask, render_template, redirect, url_for,request
from server_api import Session, updateInitiative, endPhase, adjustPoints, endTurn, newSpeaker, pauseEvent, gameStop
from sqlalchemy import select, and_
from TI_TimeTracker_DB_api import Games, Users, Factions, Events

#config=dotenv_values(".env")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
#app.config["SQLALCHEMY_DATABSE_URI"]="mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db'])

GID=1

@app.route("/")
def phase_selector():
	#this reads the current game phase and redirects the user to the representative page
	with Session() as session:
		phase=session.scalars(select(Games.GamePhase).where(Games.GameID==GID)).first()
		if phase=="Setup":
			return "just starting"	#url for setup
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
			return redirect(url_for('error_phase'))


@app.route('/welcome')
def welcome_page():
	'''
	this page displays a welcome screen for users allowing them to select an active game, view stats, or create a game
	-view game stats
	-view all time stats
	-view faction stats
	-view player stats
	Show recent 10 games with view option
	Show recent 10 players with view option
	Create new game option
	Create new player option
	
	
	'''
	with Session() as session:
		games=session.scalars(select(Games).order_by(Games.GameID).limit(10)).all()
		
@app.route('/viewGame')
def viewGame_page(GID):
	'''
	a page where users view the status of a single game
	this will pump out all the relevant stats we want to see
	'''
	pass

@app.route('/pause', methods=['GET','POST'])
def game_pause():
	#pause page, underlying code creates a pause event
	#page allows users to unpause or go through the end-game cycle
	'''
		NOTE: may want to add a "pause" state somewhere in the db  rather than just having it as
		an event so that it has some resiliency 
	'''
	if request.method=="POST":
		pauseEvent(GID,0)
		return phase_selector()
	else:
		pauseEvent(GID,1)
		return render_template("pause.html")


@app.route('/end', methods=['GET','POST'])
def end_game():
	if request.method=='POST':
		print("here")
		gameStop(GID,request.form.get('winner'))
		return phase_selector()
	else:
		with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(and_(Factions.Score,Factions.TotalTime))).all()
			return render_template("end_game.html",factions=factions)
		
@app.route('/winner', methods=['GET','POST'])
def game_winner():
	with Session() as session:
		winner=session.scalars(select(Games).where(Games.GameID==GID)).first()
		winningFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		uID=session.scalars(select(Factions.UserID).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		factions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName!=winner.GameWinner).order_by(and_(Factions.Score,Factions.TotalTime))).all()
		user=session.scalars(select(Users).where(Users.UserID==uID)).first()
		return render_template('winner.html',winningFaction=winningFaction, user=user, factions=factions)	#create this item

@app.route("/Error")
def error_phase():
	with Session() as session:
		users=session.scalars(select(Users)).all()
		#factions=session.scalars(select(Faction
		return render_template("show_users.html",users=users)

@app.route("/action", methods=['GET','POST'])#here get/post
def action_phase():
	if request.method=='POST':
		'''
		we do this twice to verify we have fresh data
		'''
		faction_check()	
		with Session() as session:
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
			'''
			else we determine if if a button was pressed related to the ative player
			such as pass or ending turn
			'''
			#items in this section shoudl be things that can only happen to the active faction
			if(request.form.get('action')):
				if(request.form['action']=="end"):
					endTurn(GID,activeFaction.FactionName,0)
				elif(request.form['action']=="pass"):
					endTurn(GID,activeFaction.FactionName,1)
					return(phase_selector())	#on everyone passing we will go to the next phase

	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
		nextFaction=factions[(factions.index(activeFaction)+1)%len(factions)]
	return render_template("action_phase.html",factions=factions, activeFaction=activeFaction, nextFaction=nextFaction)
		

@app.route("/agenda", methods=['GET','POST'])
def agenda_phase():
	#manage agenda phase
	if request.method=='POST':
		with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.TableOrder)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
			if request.form.get('action'):
				endPhase(GID,0)
				return phase_selector()
	
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		
	return render_template("agenda_phase.html",factions=factions)


@app.route("/status", methods=['GET','POST'])#here get/post
def status_phase():
	#manage status phase
	if request.method=='POST':
		with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
			if request.form.get('action'):
				endPhase(GID,0)
				return phase_selector()
	
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		
	return render_template("status_phase.html",factions=factions)


@app.route("/strategy", methods=['GET','POST'])
def strategy_phase():
	if request.method=="POST":
		#here is where we'd check the initiatives, assign them, jump to action phase
		initDict={}
		with Session() as session:
			factions=session.scalars(select(Factions.FactionName).where(Factions.GameID==GID)).all()
			#need to display in speaker order
			inits=[request.form.get(faction) for faction in factions]
			
			for faction in factions:
				if inits.count(request.form.get(faction))>1:
					print("Initiative %s selected multiple times"%request.form.get(faction))
					return redirect(url_for("strategy_phase"))
				else:
					#create our faction/init dict
					initDict[faction]=request.form.get(faction)
		updateInitiative(GID,initDict)	#update initiatives
		endPhase(GID,0)	#update phase
		return phase_selector() #move to action phase
	else:
		with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
			initiatives=range(1,9)
			return render_template("strategy_phase.html",factions=factions, initiatives=initiatives)
			
def faction_check():
	'''
	Common function that checks if points or speaker needs to be updated.
	'''
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
		'''this section checks through the from results to determine if a button
		was pressed related to a specific faction such as make speaker, +/- point
		'''
		#items in this section should be things that can happen to any faction at any time
		#this may need to be moved to a header or extension
		for faction in factions:
			if request.form.get(faction.FactionName):
				if request.form[faction.FactionName]=="speaker":
					#select a new speaker
					newSpeaker(GID,faction.FactionName)
				
				elif(request.form[faction.FactionName]=="score"):
					#add a point
					adjustPoints(GID,faction.FactionName,1)
				if(request.form[faction.FactionName]=="correct"):
					#remove a point
					adjustPoints(GID,faction.FactionName,-1)