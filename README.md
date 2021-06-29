# Neural Repair of Static Analysis Warnings

## About

This project is about training neural networks to learn from open-source static analyzers in C#. For this, it is attempted to gather all C# assemblies on [NuGet.org](https://nuget.org) that contain static analyzers, extract their analyzers & fixers and apply them to every solution in a set of open-source C# repositories. This outcoming dataset contains

* input:
  * file context, diagnostic messages and diagnostic locations
* output:
  * a specially formatted diff (ADD/REMOVE/REPLACE)

A OpenNMT Transformer model is then trained to learn what kind of fix to apply to a given input. It is then evaluated to what extent the network can COPY behaviour from diagnostics it has trained on and EXTRAPOLATE behaviour from diagnostics it has not seen in the training set.

### Use-case for COPY behaviour

Writing template-based code fixes still requires time and effort. This NN would essentially be one static analysis code fixer "to rule them all".

### Use-case for EXTRAPOLATE behaviour

Here, an appliance for the NN could be to read code comments in pull requests, treat these as diagnostic messages and recommend a suitable code fix.

## Required Dependencies

* C# / Mono
* Nuget CLI
* Roslynator.Commandline
* Python 3.7 + requirements.txt

## Pipeline

1. Run [install_dependencies.ps1](install_dependencies.ps1)
2. Run [run_info_extractor.sh](run_info_extractor.sh)
3. Run [create_raw_dataset.ps1](create_raw_dataset.ps1)
4. Run [unifying_raw_dataset.py](unifying_raw_dataset.py)
5. Run [tokenizing_unified_dataset.py](tokenizing_unified_dataset.py)
6. Run [finalize_tokenized_dataset.py](finalize_tokenized_dataset.py)
7. Run any nn in [experiment](experiment/)
8. Run [evaluate_nn_results.py](evaluate_nn_results.py)

## Problem statement for Data Collection

* Diagnostics warnings/info/errors must be matched with the diffs
* Goal: One datapoint consists of
  * 1 C# file
  * 1 type of diagnostic
  * 1 or more diagnostic messages with location
  * Diff batch (consecutive lines to be changed) to fix all diagnostic messages
* Assumption: diagnostic in one file leads to codefix
  * which consists of consecutive line changes ("diff batch")
  * in same file
  * in same line / line above / line beneath

## Work done

1. Using [get_nuget_analyzer_list.py](get_nuget_analyzer_list.py), queried NuGet.org for all packages containing "analyzer" and generated list [nuget_packages.txt](nuget_packages.txt). Later referred to as "analyzer packages".
2. Created C# project [InfoExtractor](AssemblyAnalysis/InfoExtractor) to retrieve all diagnosticIDs from DiagnosticAnalyzers and CodeFixProviders in a given C# assembly.
3. Using [install_dependencies.ps1](install_dependencies.ps1), installed all analyzer packages into a given directory. This also installed all dependencies into the same directory. Consequently using [run_info_extractor.sh](run_info_extractor.sh), which executes [InfoExtractor](AssemblyAnalysis/InfoExtractor), extracted all metadata from installed packages to [analyzer_package_details.csv](analyzer_package_details.csv).
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

* Profile self-built Roslynator to see how much time compilation takes vs applying static analysis. If compilation takes a large proportion, consider doing src-code adjustments, to avoid unnecessary compilations.
* HARD: Re-run [create_raw_dataset.ps1](create_raw_dataset.ps1) either distributed across multiple nodes (e.g. using RabbitMQ) or Roslynator src-code adjustments

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
