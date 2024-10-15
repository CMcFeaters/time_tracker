from flask import Flask, render_template, redirect, url_for,request
from server_api import Session, updateInitiative, endPhase, adjustPoints, endTurn, newSpeaker, boolEvent, gameStop, changeState, get_speaker_order
from sqlalchemy import select, and_
from TI_TimeTracker_DB_api import Games, Users, Factions, Events, Combats
import datetime

#config=dotenv_values(".env")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
#app.config["SQLALCHEMY_DATABSE_URI"]="mariadb+mariadbconnector://%s:%s@127.0.0.1:%s/%s"%(config['uname'],config['pw'],config['port'],config['db'])

GID=1

@app.route("/")
def phase_selector():
	#this reads the current game phase and redirects the user to the representative page
	with Session() as session:
		state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
		phase=session.scalars(select(Games.GamePhase).where(Games.GameID==GID)).first()
		active=session.scalars(select(Games.GameID).where(Games.Active==1)).all()
		'''if len(active)==0:
			#go to the welcome page to select a game
		else:
			GID=active.GameID
			#do all the below state stuff
		'''
		if state=="Active":
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
				print ("Action Fuck UP")
				return redirect(url_for('error_phase'))
		elif state=="Pause":
			return redirect(url_for('game_pause'))
		elif state=="Combat":
			return redirect(url_for('game_combat'))
		else:
			print ("State fuckup: %s"%state)
			return redirect(url_for('error_phase'))


@app.route('/welcome', methods=['GET','POST'])
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
		if request.method=="POST":
			#assign the selected game to be teh active one
			
			return phase_selector()
		return render_template("welcome.html",games=games,cPhase="Menu")
		
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
	with Session() as session:
		#get the state
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
	
	#check if the unpause button was pressed
	'''
	IS THERE A REASON WE USE 0/1 instead of PAUSE and UNPAUSE events.
	If we want to change this we'll have to also address the "time tracking" function
	'''
	if request.method=="POST":
		boolEvent(GID,"Pause",0)	#create an event the phase ended
		changeState(GID,"Active")		#change the state back to action phase
		return phase_selector()
	else:
		#we can only enter the pause state from the action state
		#otherwise go back to our current state
		if state=="Active":  #first time we're here
			boolEvent(GID,"Pause",1) 	#add the pause event
			changeState(GID,"Pause")	#change the state
		elif state=="Combat":	#we clicked puase while in combat, go to combat
			return redirect(url_for('game_combat'))
		return render_template("pause.html", cPhase="Paused", factions=factions)	#if the state is pause or active, go to pause page

@app.route('/combat', methods=['GET','POST'])
def game_combat():
	#pause page, underlying code creates a pause event
	#page allows users to unpause or go through the end-game cycle
	'''
		NOTE: may want to add a "combat" state somewhere in the db  rather than just having it as
		an event so that it has some resiliency 
	'''
	#will have to initiate combat event (Default start/stop time will be "now")
	#will have to stop combat event (need ot change devault stop time to "now")
	with Session() as session:	#get state and factions 
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		state=session.scalars(select(Games.GameState).where(Games.GameID==GID)).first()
	
	'''
	if we are posting to this page, we are either aborting combat (draw/misclick) or completing combat
	this determines what type of event we create and if we make an entry
	in the combat table
	'''
	if request.method=="POST":
		activeCombat=session.scalars(select(Combats).where(and_(Games.GameID==GID,Combats.Active==1))).first()
		if (request.form.get('action')):	#check if one of our action buttons was pressed
			'''
			the active combat is over, determine if we update participants or call it a draw
			'''
			
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
			boolEvent(GID,"Combat",0)	#combat endevent
			changeState(GID,"Active")	#Update teh game state
		return phase_selector()	#find our true page
	else:
		if state=="Active":	#combat can only be entered from active, otherwise we ignore
			'''
				create a new combat event, chagne stte to combat and create an entry in our
				combat table
			'''
			boolEvent(GID,"Combat",1)	#update event
			changeState(GID,"Combat")	#update state
			session.add(Combats(GameID=GID))	#create a new combat event
			session.commit()
		elif state=="Pause":	#we hit combat  while in pause
			return redirect(url_for('game_pause'))	#return to pause page
		return render_template("combat.html", cPhase="Combat", factions=factions)	#go to the combat page (active/combat) state


@app.route('/end', methods=['GET','POST'])
def end_game():
	'''
		this page allows teh user to select the game being over
	'''
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
	'''
	this is the page you get when the game is oVER!
	'''
	with Session() as session:
		winner=session.scalars(select(Games).where(Games.GameID==GID)).first()
		winningFaction=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		uID=session.scalars(select(Factions.UserID).where(Factions.GameID==GID,Factions.FactionName==winner.GameWinner)).first()
		factions=session.scalars(select(Factions).where(Factions.GameID==GID,Factions.FactionName!=winner.GameWinner).order_by(and_(Factions.Score,Factions.TotalTime))).all()
		user=session.scalars(select(Users).where(Users.UserID==uID)).first()
		return render_template('winner.html',winningFaction=winningFaction, user=user, factions=factions)	#create this item

@app.route("/Error")
def error_phase():
	'''
	default error page for when somethign goes wrong
	'''
	with Session() as session:
		users=session.scalars(select(Users)).all()
		#factions=session.scalars(select(Faction
		return render_template("show_users.html",users=users)


@app.route("/footer_update", methods=['POST'])
def footer_update():
	'''
	this function is called when one of the buttons in the footer is pressed
	it updates speaker, or score, then redirects to the appropriate URL function
	'''
	print("hello")
	if request.method=='POST':
		with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
			'''this section checks through the from results to determine if a button
			was pressed related to a specific faction such as make speaker, +/- point
			'''
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
	return phase_selector()

@app.route("/action", methods=['GET','POST'])#here get/post
def action_phase():
	'''
	action phase page allowing you to end/pass turns,
	display turn order
	'''
	if request.method=='POST':

		with Session() as session:
			'''
			end/pass active factions turn
			'''
			activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()

			if(request.form.get('action')):
				if(request.form['action']=="end"):
					endTurn(GID,activeFaction.FactionName,0)
				elif(request.form['action']=="pass"):
					endTurn(GID,activeFaction.FactionName,1)
					return(phase_selector())	#on everyone passing we will go to the next phase

	with Session() as session:
		'''find the next faction or list none if there is no next'''
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		activeFaction=session.scalars(select(Factions).where(Factions.GameID==GID, Factions.Active==1)).first()
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
		
			
	return render_template("action_phase.html",factions=factions, activeFaction=activeFaction, nextFaction=nextFaction, cPhase="Action")
		

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
		sFactions=get_speaker_order(GID,factions)
	return render_template("agenda_phase.html",factions=factions,sFactions=sFactions,cPhase="Agenda")


@app.route("/status", methods=['GET','POST'])#here get/post
def status_phase():
	'''
		this page displays the steps for the status phase and allows you to move to the next phase
	'''
	
	if request.method=='POST':
		'''with Session() as session:
			factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
			for faction in factions:
				if request.form.get(faction.FactionName):
					adjustPoints(GID,faction.FactionName,int(request.form.get(faction.FactionName)))
		'''
		if request.form.get('action'):
			endPhase(GID,0)
			return phase_selector()

	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID).order_by(Factions.Initiative)).all()
		
	return render_template("status_phase.html",factions=factions)


@app.route("/strategy", methods=['GET','POST'])
def strategy_phase():
	'''
		this page allows the user to select initiatives
		must select different initiatives for each faction
	'''
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
			sFactions=get_speaker_order(factions)
			initiatives=range(1,9)
			#factions: the normal setup of factions used for the footer
			#iFactions: factions arranged by speaker order user for the display
			#initiatives: a range of numbers 1-8 for selecting initiative
			return render_template("strategy_phase.html",factions=factions, sFactions=sFactions, initiatives=initiatives, cPhase="Strategy")

