all: release

release: clean
	@echo. && @echo ====== Building release package ======
	mkdir release
	copy /Y src\*.py release
	mkdir release\tools
	copy /Y src\tools\*.py release\tools
	mkdir release\tools\libjpeg
	copy /Y src\tools\libjpeg\* release\tools\libjpeg
	mkdir release\html
	copy /Y src\html\* release\html
	mkdir release\html\js
	copy /Y src\html\js\*.js release\html\js
	mkdir release\html\css
	sass --no-source-map src\html\css:release\html\css
	copy /Y src\*.ini release
	copy /Y requirements.txt release
	7z a xrit-rx.zip ./release/*
	rmdir /S /Q release

clean:
	@echo. && @echo ====== Cleaning development environment ======
	if exist release rmdir /S /Q release
	if exist src\__pycache__ rmdir /S /Q src\__pycache__
	if exist src\received rmdir /S /Q src\received
	if exist xrit-rx.zip del /Q xrit-rx.zip

.PHONY: all clean release
