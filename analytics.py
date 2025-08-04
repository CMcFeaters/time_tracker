from TI_TimeTracker_DB_api import engine, Games, Users, Factions, Events, createNew, clearAll, Combats
from sqlalchemy import select, or_, delete, update
from sqlalchemy.orm import sessionmaker
from datetime import timedelta
import statistics
Session=sessionmaker(engine)

def get_turn_stats(GID,faction):
	'''
		provide round and faction data for a faction
		input: faction.FactionName
	'''
	fDict={'turnData':[],'totalTime':timedelta(seconds=0)}
	with Session() as session:
		starts=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction, Events.EventType=="StartTurn").order_by(Events.EventID)).all()
		ends=session.scalars(select(Events).where(Events.GameID==GID,Events.FactionName==faction, or_(Events.EventType=="EndTurn",Events.EventType=="PassTurn")).order_by(Events.EventID)).all()
		#[print(f'{starts[i].EventID}-{ends[i].EventID}') for i in range(0,len(starts))]
		fDict['turnCount']=len(starts)
		print(f"Turns: {fDict['turnCount']}")
		for i in range(0,len(starts)):
			#ingnore pauses for now
			turnTime=ends[i].EventTime-starts[i].EventTime
			fDict['turnData'].append({'number':i,'time':turnTime,'round':starts[i].Round})
			fDict['totalTime']=turnTime+fDict['totalTime']
		for i in range(0,len(starts)):
			#print(f"Round: {fDict['turnData'][i]['round']}: Turn {fDict['turnData'][i]['number']} - {fDict['turnData'][i]['time']}")
			roundTimes=[fDict['turnData'][i]['time'] for i in range(0,fDict['turnCount']-1)]
		print(f'Shortest Round: {min(roundTimes)}')
		print(f'Median Round: {statistics.median(roundTimes)}')
		print(f'Longest Round: {max(roundTimes)}')
		print(f'Average Round: {fDict["totalTime"]/fDict["turnCount"]}')
		print(f"TotalTime: {fDict['totalTime']}")
	
	
def print_stats(GID):
	'''
	gets some round data
	'''
	with Session() as session:
		factions=session.scalars(select(Factions).where(Factions.GameID==GID)).all()
		for faction in factions:
			
			print(f'Faction {faction.FactionName} played by {faction.UserName}')
			print(f'Score: {faction.Score}')
			get_turn_stats(GID,faction.FactionName)
			
print_stats(2)