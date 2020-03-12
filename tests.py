import os
import subprocess

files = os.listdir(".\\cases\\")

with open("TestResults.txt", "w") as myfile:
		myfile.write("CASES:\n")

i = 0
while i < len(files) - 12: # REMOVE THE 12 LATER WHEN IMPLEMENTED THE HETEROGENEUS

	string = "compare-object (cat .\\cases\\{}) (cat .\\cases\\{} | C:\\DevTools\\Python\\Python35\\python exercise.py)".format(files[i+1], files[i])
	process = subprocess.Popen(["powershell", string], stdout=subprocess.PIPE)
	result = process.communicate()[0]
	
	testResult = str(files[i]) + ": "
	if (result == b''):
		testResult += "PASSED\n"
	else:
		testResult += "FAILED\n"

	with open("TestResults.txt", "a") as myfile:
		myfile.write(testResult)

	i += 2

files = os.listdir(".\\statement\\")

with open("TestResults.txt", "a") as myfile:
		myfile.write("\nSTATEMENT:\n\n")

i = 0
while i < len(files):

	string = "compare-object (cat .\\statement\\{}) (cat .\\statement\\{} | C:\\DevTools\\Python\\Python35\\python exercise.py)".format(files[i+1], files[i])
	process = subprocess.Popen(["powershell", string], stdout=subprocess.PIPE)
	result = process.communicate()[0]
	
	testResult = str(files[i]) + ": "
	if (result == b''):
		testResult += "PASSED\n"
	else:
		testResult += "FAILED\n"

	with open("TestResults.txt", "a") as myfile:
		myfile.write(testResult)

	i += 2
