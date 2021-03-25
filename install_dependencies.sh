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

# TODO: Extract all diagnostic ids from dlls and write into csv-file analyzer_package_details.csv

# Most of required code is in "Applying Analyzers" project (Target: .Net Framework 4.7)
# --> No remote Desktop needed.

# Columns: ANALYZER_PACKAGE,ANALYZER_ASSEMBLY,TYPE,DIAGNOSTIC_ID
# Example:
# Microsoft.CodeAnalysis.NetAnalyzers.5.0.3,Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll,DIAGNOSTIC_ANALYZER,CA1827
# Microsoft.CodeAnalysis.NetAnalyzers.5.0.3,Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll,CODEFIX_PROVIDER,CA1827
# Microsoft.CodeAnalysis.NetAnalyzers.5.0.3,Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll,DIAGNOSTIC_ANALYZER,CA1401
# Microsoft.CodeAnalysis.NetAnalyzers.5.0.3,Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll,DIAGNOSTIC_ANALYZER,CA1806
