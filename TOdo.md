(DONE)Add all new factions to selection pool
Add abilty to "shelve" games and shelve all old games
    (done) add "hidden" true/false
    (done) when displaying games if "Shelve" don't show it
Add Ral Nel ability to "unpass"
    This needs to be a stored bit in the game (ral Nel)
    if ral nel, every time there is a final pass, you need to ask if ral nel is doing their hero
    once they've done it, set ral nel to 0
    if ral nel is in the game, set ral nel to 1 at game creation
    need to ensure ralnel is easily put back into the timing rotation


(general)
	Round needs to start on strategy start and end on status completion
    add start phase for agenda, strat, status, etc.
    end tactical phase on end turn
    add pause to stop

(Turns support)
    (DONE,tested)endturn
    (Done) end phase
    (DONE,tested)endstrat
    gamestop
    undoendturn (Add und turn)
    undoendstrat (Add undo turn)

REmove PassTurn
(Events Table)
    Add primary and secondary columnns (0=no, 1=yes)
    ChangeMisc Data to Turn Data, 0=normal, 1=pass, 2=combat
(Turns Tabls)
    add timestamp to turn table
    turn number shoudl auto-increment (db)

(MISC DATA)
    MISC DATA IS USED INCONSISTENTLY DEPENDING ON THE STATE, need to correct.  We shouldn't use it as primary secondary identifier, make a new column for that
    undoendstrat
        used as 1=primary, 2=secondary.  should be replaced with secondary/primary column
    (done)undoendturn
        used to determine which strategy card was used in StratEnd event.  Changed to use column StrategyData which holds same info.
    endturn
        0,1,2=normal,combat,pass end turn info.  Should be replaced with EndType column
    startstrat
        sets miscdata =2 since this is only called during secondaries.  Should be replaced with primary_secondary
    closestrat
        sets miscdata=whatever the current strat is, does similar for strategydata.  should be removed once dependencies are identified add removed
    boolevent
        uses miscdata to indicate pause (1) and unpause(0) status.  Replace with PAUSE column in GameState.  
    adjustpoints
        uses miscdata to indicate total score for player.  Replace with SCORE column. 
        Fill score column on all events or just during score?
    phasechangedetails
        uses miscdata keeps track of round.  should be removed once dependencies are idetnfied and removed
    changestatestrat
        sets miscdata=whatever teh current strat is, does similar for strategy data.  shoudl be removed once dependencies are identified
    endphase
        uses miscdata to determine if game is paused when ending game.  if paused, adds an unpause event.  Either correct during pause, or prevent "end game" from being pressed during pause.  

transfer Pause to use the game table
ensure the we are looking up game info for the current strategy card
use updated GameStrategyName and GameStrategyNumber for game table

XUpdate tables using alembic
Do the data transfer
    Events:
        StrategyData-> Strategycardname/number
        ScoreEvents->scoretotal/score
        MiscData->TacticalInfo/StrategicActionInfo
    Turns:
        TurnInfo/MiscData -> StratCardName/Number, StrategicActionInfo
        TurnInfo-> TacticalInfo
        TurnInfo-> PhaseInfo
Update the data (x) and methods (y) for creating new data to reflect modifications
    Events:
        X,Y-StrategyData-> Strategycardname/number
        Y - ScoreEvents->scoretotal/score
        X,Y-MiscData->TacticalInfo/StrategicActionInfo
        X-EndState-Strategic ->Strategetcardname/number/faction
        X-startTurn-Strategic ->strategycardname/number
    Turns:
        X,Y-TurnInfo/MiscData -> StratCardName/Number, StrategicActionInfo
        X,Y -TurnInfo-> TacticalInfo
        X,Y -TurnInfo-> PhaseInfo
    XY-Pause:
        XY-GamePause
    XY-GameStrategy->GameStrategyCardNumber/Name
        -I don't know where we set gamestrategy?
        #we are udpading gamedata and investigating how we know what strategy card we're using, line 874
        changestatestrat- sets the strategy
        changestate (if strategy is current) clears the game strat
        #where do we find the strategy card info? 
store enums in database
-list enums
-Tactical Action Name
-Strategy Card Name
-Strategic Action Name
-phase data
-state data
Delete the old columns using alembic
-tacticalinfo
-miscdata
-strategydata
Undos and TurnTable
X-Fill in all turn times

SHOULD ALWYS INDICATE THE PHASE of the event, no nulls should exist.
SHOULD ALWAYS INDICATE THE STATE OF THEV EVENT, NO NULLS SHOULD EXIST
