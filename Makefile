# Opzione con && (stessa riga logica)
run:
	. venv/bin/activate && python3 main.py
back:
	screen -S bot_azioni && . venv/bin/activate && python3 main.py

