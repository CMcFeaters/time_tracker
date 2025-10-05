# time_tracker
This time tracker is intended to support event tracking in a twilight imperium game.  It is also intended to be capable of being synched with the pictures taken by TI_Camera.

to clear database: 
python .\server_api.py off

to run in localhost only:
flask --app ti_page run

to run in network mode:
flask --app ti_page run --host=0.0.0.0

test