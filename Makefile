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
	rmdir /S /Q release

.PHONY: all clean
