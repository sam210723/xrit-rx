all: release

release:
	if not exist release mkdir release
	copy /Y src\*.py release
	copy /Y src\tools\*.py release
	copy /Y src\*.ini release
	copy /Y src\*.bat release
	copy /Y src\*.sh release
	copy /Y requirements.txt release

clean:
	if exist release rmdir /S /Q release
	if exist src\__pycache__ rmdir /S /Q src\__pycache__
	if exist src\received rmdir /S /Q src\received

.PHONY: all clean
