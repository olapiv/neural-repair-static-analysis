#!/bin/bash

# TODO: Install Roslynator if not installed & add to PATH

while read line do
    # The roslynator tag "--analyzer-assemblies" accepts directories to search in recursively.
    # The downloaded NuGet package therefore does not need further parsing.

    nuget install $line -OutputDirectory nuget_analyzer_packages
    # The package version is included in the directory name. E.g.:
    #       Microsoft.CodeAnalysis.NetAnalyzers.5.0.3
    #       StyleCop.Analyzers.1.1.118

done < nuget_packages.txt

# TODO: Execute C# Project AssemblyAnalysis to generate analyzer_package_details.csv
