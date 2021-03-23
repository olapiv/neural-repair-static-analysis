#!/bin/bash

# Install Roslynator if not installed
# Add Roslynator to path
# 

while read line do
    nuget install $line -OutputDirectory analyzer_assemblies
    # TODO: Save package version
done < nuget_packages.txt

# TODO: Extract all diagnostic ids from dlls and write into csv-file