# InfoExtractor

Previously, all NuGet packages with the query "analyzer" were fetched from nuget.org and installed. This project extracts metadata from these NuGet packages to understand which diagnostics they support or fix. All results are saved to [analyzer_package_details.csv](../../analyzer_package_details.csv).

The [AssemblyParser.cs](AssemblyParser.cs) in this project is largely copied/inspired by [JosefPihrt/Roslynator](https://github.com/JosefPihrt/Roslynator).
