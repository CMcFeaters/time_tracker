CREATE USER IF NOT EXISTS 'admin@localhost' IDENTIFIED BY 'admin123';
CREATE USER IF NOT EXISTS 'gatechUser@localhost' IDENTIFIED BY 'gatech123';

DROP DATABASE IF EXISTS TI_TIME_TRACKER; 
SET default_storage_engine=InnoDB;
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS TI_TIME_TRACKER 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS TI_TIME_TRACKER.Users (
	UserID integer(3) NOT NULL AUTO_INCREMENT,
	Username varchar(50) NOT NULL,
	PRIMARY KEY (UserID)
	);

 
CREATE TABLE IF NOT EXISTS TI_TIME_TRACKER.Game(
	GameID integer(3) NOT NULL AUTO_INCREMENT,
	GameDate DateTime NOT NULL,
	GamePhase varchar(50) NOT NULL,
	GameRound integer(2) NOT NULL,
	ActiveFaction varchar(50),
	PRIMARY KEY (GameID)
	);

ALTER TABLE TI_TIME_TRACKER.Game
	ADD CONSTRAINT fk_Game_ActiveFaction FOREIGN KEY (ActiveFaction) REFERENCES Faction (FactionName);
	
CREATE TABLE IF NOT EXISTS TI_TIME_TRACKER.Faction (
	FactionName varchar(50) NOT NULL,
	GameID integer(3) NOT NULL,
	UserID integer(3) NOT NULL,
	TableOrder integer(2) NOT NULL,
	Speaker boolean NOT NULL,
	Score integer(2) NOT NULL,
	TotalTime Time NOT NULL,
	Initiative integer (2) NOT NULL,
	PRIMARY KEY (FactionName,GameID)
	);

ALTER TABLE TI_TIME_TRACKER.Faction
	ADD CONSTRAINT fk_Faction_GameID FOREIGN KEY (GameID) REFERENCES Game (GameID),
	ADD CONSTRAINT fk_Faction_UserID FOREIGN KEY (UserID) REFERENCES Users (UserID);

CREATE TABLE IF NOT EXISTS TI_TIME_TRACKER.Events (
	EventTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
	GameID integer(3) NOT NULL,
	FactionName varchar(50),
	EventType varchar(50) NOT NULL,
	Phase varchar(50),
	RoundNum integer(2),
	PRIMARY KEY (EventTime,GameID)	
	);
	
ALTER TABLE TI_TIME_TRACKER.Events
	ADD CONSTRAINT fk_Events_GameID FOREIGN KEY (GameID) REFERENCES Game (GameID),
	ADD CONSTRAINT fk_Events_FactionName FOREIGN KEY (FactionName) REFERENCES Faction (FactionName);