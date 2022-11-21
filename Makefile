init:
	pip3 install -r requirements.txt

start:
	python3 uboot/core.py

fix:
	autopep8 --recursive --aggressive --in-place uboot
