run:
	source venv/bin/activate && python main.py

init:
	python3 -m venv venv

install:
	source venv/bin/activate && pip install -r requirements.txt
