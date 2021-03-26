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

## TODO

* Check which diagnostics don't have CodeFixProviders
* Understand why some assemblies have duplicate DIAGNOSTIC_ANALYZERs, E.g.:
  `Microsoft.CodeQuality.Analyzers.3.3.2,Microsoft.CodeQuality.Analyzers,DIAGNOSTIC_ANALYZER,CA2225`

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
