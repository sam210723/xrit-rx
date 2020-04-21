all: release

release:
	if exist release rmdir /S /Q release
	mkdir release
	copy /Y src\*.py release
	mkdir release\tools
	copy /Y src\tools\*.py release\tools
	copy /Y src\*.ini release
	copy /Y src\*.bat release
	copy /Y src\*.sh release
	copy /Y requirements.txt release
	echo xrit-rx v?.? > release\README.txt
	echo.>> release\README.txt
	echo See https://github.com/sam210723/xrit-rx for documentation >> release\README.txt

clean:
	if exist release rmdir /S /Q release
	if exist src\__pycache__ rmdir /S /Q src\__pycache__
	if exist src\received rmdir /S /Q src\received	

.PHONY: all clean release
