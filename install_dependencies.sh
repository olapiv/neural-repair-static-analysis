#!/bin/bash

# Required:
# * Python3
# * C#/Mono
# * nuget CLI

python3 -m venv ./venv
source venv/bin/activate
pip install -r requirements.txt
python3 get_nuget_analyzer_list.py

while read line; do
    # The roslynator tag "--analyzer-assemblies" accepts directories to search in recursively.
    # The downloaded NuGet package therefore does not need further parsing.

    nuget install $line -OutputDirectory nuget_analyzer_packages
    # The package version is included in the directory name. E.g.:
    # --> Microsoft.CodeAnalysis.NetAnalyzers.5.0.3
    # --> StyleCop.Analyzers.1.1.118

done <nuget_packages.txt

NEW_CSV="True"
for ANALYZER_PACKAGE in nuget_analyzer_packages/*/; do
    echo "ANALYZER_PACKAGE: $ANALYZER_PACKAGE"
    # Command for Mac:
    mono AssemblyAnalysis/InfoExtractor/bin/Debug/InfoExtractor.exe $ANALYZER_PACKAGE "analyzer_package_details.csv" $NEW_CSV
    NEW_CSV="False"
done
