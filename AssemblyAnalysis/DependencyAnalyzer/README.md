# DependencyAnalyzer

Previously, all NuGet packages with the query "analyzer" were fetched from nuget.org, and all their supported & fixable diagnostics were extracted into [analyzer_package_details.csv](../../analyzer_package_details.csv). In there, a large number of diagnostic ID duplications was observed. Even though only having installed the latest NuGet packages, many diagnostic IDs originated from different versions of the same packages. In this C# project, the dependencies between the NuGet analyzer packages is explored and saved to [nuget_deps.json](../../nuget_deps.json).

It turns out that a number of analyzer packages bundle other analyzer packages and may not necessarily contribute with own DiagnosticAnalyzers / CodeFixProviders.
