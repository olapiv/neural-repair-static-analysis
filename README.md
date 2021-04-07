# Neural Repair of Static Analysis Warnings

## Workflow

1. Run `install_dependencies.sh`
2. Run `create_dataset.sh`

## Required Dependencies

* C# / Mono
* Nuget CLI
* Roslynator.Commandline

## Problem statement for Data Collection

* Diagnostics warnings/info/errors must be matched with the diffs
* First goal: One datapoint consists of
    i. 1 C# file
    i. >= 1 Diagnostic message & location
    i. Diff for same C# file
* Assumption: diagnostic in one file leads to codefix in same file

## Work done

1. Using  `get_nuget_analyzer_list.py`, queried NuGet.org for all packages containing "analyzer" and generated list `nuget_packages.txt`. Later referred to as "analyzer packages".
2. Created C# project `AssemblyAnalysis/InfoExractor` to retrieve all diagnosticIDs from DiagnosticAnalyzers and CodeFixProviders in a given C# assembly.
3. Using `install_dependencies.sh`, installed all analyzer packages into a given directory. This also installed all dependencies into the same directory. Consequently using `AssemblyAnalysis/InfoExractor`, extracted all metadata from installed packages to `analyzer_package_details.csv`.
4. Due to large amounts of diagnostic ID duplications in `analyzer_package_details.csv`, analyzed dependency structure of installed packages using C# project `AssemblyAnalysis/DependencyAnalyzer`. Saved results in `nuget_deps.json`. Turns out, a number of analyzer packages bundle other analyzer packages and may not necessarily contribute with own DiagnosticAnalyzers / CodeFixProviders.
5. Using `analyzing_analyzers.py`, created further statistics to the installed analyzer packages.
6. Using `create_raw_dataset.sh`, generated `roslynator analyze` vs `roslynator fix` outputs on repositories saved in `github_repos.txt`. Sample `roslynator analyze` output can be viewed in `sample_roslynator_analysis.xml`.

## TODO

* Understand why some assemblies have duplicate DIAGNOSTIC_ANALYZERs, E.g.:
  `Microsoft.CodeQuality.Analyzers.3.3.2,Microsoft.CodeQuality.Analyzers,DIAGNOSTIC_ANALYZER,CA2225`

Later:

* How many diff at the end?
* No. of diffs produced per analyzer?
* Distribution of the size of the diffs?

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
