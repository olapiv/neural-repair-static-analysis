# Neural Repair of Static Analysis Warnings

## Workflow

1. Run [install_dependencies.ps1](install_dependencies.ps1)
2. Run [create_raw_dataset.ps1](create_raw_dataset.ps1)
3. Run [refining_raw_dataset.py](refining_raw_dataset.py)

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

1. Using [get_nuget_analyzer_list.py](get_nuget_analyzer_list.py), queried NuGet.org for all packages containing "analyzer" and generated list [nuget_packages.txt](nuget_packages.txt). Later referred to as "analyzer packages".
2. Created C# project [InfoExtractor](AssemblyAnalysis/AssemblyAnalysis/InfoExtractor) to retrieve all diagnosticIDs from DiagnosticAnalyzers and CodeFixProviders in a given C# assembly.
3. Using [install_dependencies.ps1](install_dependencies.ps1), installed all analyzer packages into a given directory. This also installed all dependencies into the same directory. Consequently using [InfoExtractor](AssemblyAnalysis/AssemblyAnalysis/InfoExtractor), extracted all metadata from installed packages to [analyzer_package_details.csv](analyzer_package_details.csv).
4. Due to large amounts of diagnostic ID duplications in [analyzer_package_details.csv](analyzer_package_details.csv), analyzed dependency structure of installed packages using C# project [DependencyAnalyzer](AssemblyAnalysis/AssemblyAnalysis/DependencyAnalyzer). Saved results in [nuget_deps.json](nuget_deps.json). Turns out, a number of analyzer packages bundle other analyzer packages and may not necessarily contribute with own DiagnosticAnalyzers / CodeFixProviders.
5. Using [analyzing_analyzers.py](analyzing_analyzers.py), created further statistics to the installed analyzer packages.
6. Using [create_raw_dataset.ps1](create_raw_dataset.ps1), generated `roslynator analyze` vs `roslynator fix` outputs on repositories listed in [github_repos.csv](github_repos.csv). Sample `roslynator analyze` output can be viewed in [sample_roslynator_analysis.xml](sample_roslynator_analysis.xml).
7. Using [parsing_diffs.py](parsing_diffs.py) and [refining_raw_dataset.py](refining_raw_dataset.py), created dataset, which can fed into NN. Different data samples can be viewed in [sample_refined_data_model.json](sample_refined_data_model.json).

## TODO

* Create seq-2-seq model
* Re-run [create_raw_dataset.ps1](create_raw_dataset.ps1) on one machine, parallelized across repositories to avoid faulty data
* Profile self-built Roslynator to see how much time compilation takes vs applying static analysis. If compilation takes a large proportion, consider doing src-code adjustments (e.g. built-in socket), to avoid unnecessary compilations.
* HARD: Re-run [create_raw_dataset.ps1](create_raw_dataset.ps1) either distributed across multiple nodes (e.g. using RabbitMQ) or Roslynator src-code adjustments
* Gather metadata around dataset:
    1. No. diffs
    1. No. of diffs per analyzer
    1. Distribution of diff size

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
