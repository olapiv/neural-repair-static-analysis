# Neural Repair of Static Analysis Warnings

## Workflow

1. Run `install_dependencies.sh`
2. Run `create_dataset.sh`

## Problem statement for Data Collection

* Diagnostics warnings/info/errors must be matched with the diffs
* First goal: One datapoint consists of
    i. 1 C# file
    i. >= 1 Diagnostic message & location
    i. Diff for same C# file
* Assumption: diagnostic in one file leads to codefix in same file

## TODO

* Check which diagnostics don't have CodeFixProviders

## Links

* [Documenation to Search packages with Nuget Rest API](https://docs.microsoft.com/en-us/nuget/api/search-query-service-resource)
* [Github repos from Learning to Represent Edits](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits/blob/master/sampled_repos.txt)
