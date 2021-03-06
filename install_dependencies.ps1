#!/bin/bash

# Required:
# * Python3
# * Nuget CLI
# * C#/Mono

python -m venv ./venv
venv/Scripts/Activate.ps1
pip install -r requirements.txt

## Generate nuget_packages.txt:
python3 get_nuget_analyzer_list.py

## Install all nuget packages in nuget_packages.txt:
foreach($line in Get-Content .\nuget_packages.txt) {
    # The roslynator tag "--analyzer-assemblies" accepts directories to search in recursively.
    # The downloaded NuGet package therefore does not need further parsing.

    ./nuget.exe install $line -OutputDirectory nuget_analyzer_packages
    # The package version is included in the directory name. E.g.:
    # --> Microsoft.CodeAnalysis.NetAnalyzers.5.0.3
    # --> StyleCop.Analyzers.1.1.118
}
