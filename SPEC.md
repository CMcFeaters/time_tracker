# time_tracker
SPECIFICATION

Users interface via browser
Data is stored in a DB
Data can be synched to TI_camera data
Users have long term records

A user can view, edit, and create new "users" which must have unique names

A user can view all avaible games (closed or not).
A user can create new games which requires them to enter the game date, select players from player pool, and assign players factions.
A user can open an available game.  Games that have ended can be viewed, games that are active can be managed.

When a user selects to manage a game, they are brough to the game management screen.  
Information Diplayed to user:
-The score
-The Round
-The Active Phase
-Speaker order
-The Active Player (Action)
-Passed Status (Action)
-Initiative (Action/status)
-Total Active Time (Status)
-During Action and status phase players are shown in initiative order
-During Agenda and Strategy phase players are shown in speaker order

User Capabilities:
-Pause/un-pause (Anytime)
	--If paused, the only thing you can do is unpause, this is just an event used to provide higher accuracy of play time
-Adjust Points (up or down) [any time to support admin]
-Assign Speaker [anytime to support admin]
-Assign Initiative [anytime to support admin, speaker order during strat phase]
-Manipulate the game phase.  (phase dependent, see state machine)
-End Active player turn (action phase only)
-Pass Active Player turn (no more turns, action phase only)


Game Phase State Machine:
Initiate to Strategy Phase
Status to Agenda Phase
Status to Strategy Phase
Agenda Phase to Strategy Phase
Strategy to Action Phase
Status to End Phase (10 points)
Agenda to End Phase (10 points)
Action to End Phase (10 points)




