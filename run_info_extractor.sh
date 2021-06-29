#!/bin/bash

# InfoExtractor is executed in a loop here, since the Mono runtime crashes occasionally, which cannot
# be handled in an exception, so the application always stops. Here, the script continues.

NEW_CSV="True"
for ANALYZER_PACKAGE in nuget_analyzer_packages/*/; do
    echo "ANALYZER_PACKAGE: $ANALYZER_PACKAGE"
    # Command for Mac:
    mono AssemblyAnalysis/InfoExtractor/bin/Debug/InfoExtractor.exe $ANALYZER_PACKAGE "analyzer_package_details_new.csv" $NEW_CSV
    NEW_CSV="False"
done
