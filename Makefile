all: release

release: clean
	mkdir release
	copy /Y src\*.py release
	mkdir release\tools
	copy /Y src\tools\*.py release\tools
	mkdir release\html
	copy /Y src\html\* release\html
	mkdir release\html\js
	copy /Y src\html\js\*.js release\html\js
	mkdir release\html\css
	copy /Y src\html\css\*.css release\html\css
	copy /Y src\*.ini release
	copy /Y src\*.bat release
	copy /Y src\*.sh release
	copy /Y requirements.txt release

clean:
	if exist release rmdir /S /Q release
	if exist src\__pycache__ rmdir /S /Q src\__pycache__
	if exist src\received rmdir /S /Q src\received	

.PHONY: all clean release
