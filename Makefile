init:
	pip3 install -r requirements.txt

fix:
	autopep8 --recursive --aggressive --in-place uboot

set-env:
	. ./venv/bin/activate

start: set-env
	python3 uboot/core.py

test: set-env
		watchmedo auto-restart \
		--patterns="*.py" \
		--directory="uboot/"\
		--recursive \
		python3 uboot/core.py
