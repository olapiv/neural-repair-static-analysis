import json

with open('nuget_api_response.json') as f:
    responseDict = json.load(f)

nugetPackages = []
for nugetPackage in responseDict["data"]:
    nugetPackages += [nugetPackage["id"]]

with open('nuget_packages.txt', 'w') as f:
    for nugetPackage in nugetPackages:
        f.write(nugetPackage + "\n")
