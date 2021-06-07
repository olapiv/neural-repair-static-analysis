# Neural Repair of Static Analysis Warnings

## Workflow

1. Run [install_dependencies.ps1](install_dependencies.ps1)
2. Run [create_raw_dataset.ps1](create_raw_dataset.ps1)
3. Run [unifying_raw_dataset.py](unifying_raw_dataset.py)
4. Run [tokenizing_unified_dataset.py](tokenizing_unified_dataset.py)
5. Run [finalize_tokenized_dataset.py](finalize_tokenized_dataset.py)
6. Run [nn](nn)
7. Run [evaluate_nn_results.py](evaluate_nn_results.py)

## Required Dependencies

* C# / Mono
* Nuget CLI
* Roslynator.Commandline
* Python 3.7 + requirements.txt

## Problem statement for Data Collection

* Diagnostics warnings/info/errors must be matched with the diffs
* Goal: One datapoint consists of
  * 1 C# file
  * 1 or more diagnostic messages with location
  * Diff to fix this specific diagnostic
* Assumption: diagnostic in one file leads to codefix
  * which consists of consecutive line changes ("diff batch")
  * in same file
  * in same line / line above / line beneath

## Work done

1. Using [get_nuget_analyzer_list.py](get_nuget_analyzer_list.py), queried NuGet.org for all packages containing "analyzer" and generated list [nuget_packages.txt](nuget_packages.txt). Later referred to as "analyzer packages".
2. Created C# project [InfoExtractor](AssemblyAnalysis/InfoExtractor) to retrieve all diagnosticIDs from DiagnosticAnalyzers and CodeFixProviders in a given C# assembly.
3. Using [install_dependencies.ps1](install_dependencies.ps1), installed all analyzer packages into a given directory. This also installed all dependencies into the same directory. Consequently using [InfoExtractor](AssemblyAnalysis/InfoExtractor), extracted all metadata from installed packages to [analyzer_package_details.csv](analyzer_package_details.csv).
4. Due to large amounts of diagnostic ID duplications in [analyzer_package_details.csv](analyzer_package_details.csv), analyzed dependency structure of installed packages using C# project [DependencyAnalyzer](AssemblyAnalysis/DependencyAnalyzer). Saved results in [nuget_deps.json](nuget_deps.json). Turns out, a number of analyzer packages bundle other analyzer packages and may not necessarily contribute with own DiagnosticAnalyzers / CodeFixProviders.
5. Using [analyzing_analyzers.py](analyzing_analyzers.py), created further statistics to the installed analyzer packages.
6. Using [create_raw_dataset.ps1](create_raw_dataset.ps1), generated `roslynator analyze` vs `roslynator fix` outputs on repositories listed in [github_repos.csv](github_repos.csv). Sample `roslynator analyze` output can be viewed in [sample_roslynator_analysis.xml](sample_roslynator_analysis.xml).
7. Using [parsing_diffs.py](parsing_diffs.py) and [unifying_raw_dataset.py](unifying_raw_dataset.py), created dataset, which merges previously created raw analysiis files and diffs. Different data samples can be viewed in [sample_unified_data_model.json](sample_unified_data_model.json).
8. Since a large proportion of the dataset are refactorings, which includes adding whitespace, line breaks or documentation ("trivia"), created custom [regex_lexer.py](regex_lexer.py), based on Python library "Pygments". It parses CSharp with trivia and switches state when reading line/break comments or string literals. See corresponding test-cases in [regex_lexer_tests.py](regex_lexer_tests.py).
9. Using the [regex_lexer.py](regex_lexer.py), tokenized file contexts, diagnostic messages and diff batches in [tokenizing_unified_dataset.py](tokenizing_unified_dataset.py) creating a tokenized dataset.
10. Finalized the dataset for OpenNMT in [finalize_tokenized_dataset.py](finalize_tokenized_dataset.py), including splitting datapoints into training/testing/validation fractions.
11. Created a basic Transformer OpenNMT NN model in [nn](nn), to see whether a NN can learn from the dataset.
12. Using [evaluate_nn_results.py](evaluate_nn_results.py), evaluated:
    1. how many datapoints are predicted correctly
    2. which diagnostics perform best/worst
    3. how diagnostics performed in test that were vs. weren't already in the training set (copied vs extrapolated)
    4. which diagnostics performed most ambiguously `abs(accuracy - 0.5).sort_ascending()`
    5. how the number of datapoints for a diagnostic in train relates to it's performance in test

## TODO later

* Re-run [create_raw_dataset.ps1](create_raw_dataset.ps1) on one machine, parallelized across repositories to avoid faulty data
* Profile self-built Roslynator to see how much time compilation takes vs applying static analysis. If compilation takes a large proportion, consider doing src-code adjustments (e.g. built-in socket), to avoid unnecessary compilations.
* HARD: Re-run [create_raw_dataset.ps1](create_raw_dataset.ps1) either distributed across multiple nodes (e.g. using RabbitMQ) or Roslynator src-code adjustments
* Gather metadata around dataset:
    1. No. diffs
    2. No. of diffs per analyzer
    3. Distribution of diff size

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
