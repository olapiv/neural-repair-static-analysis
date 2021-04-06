using System;
using System.IO;
using NuGet;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using NuGet.Packaging;


// Inspiration from https://stackoverflow.com/a/6744794/9068781
namespace DependencyAnalyzer
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            Dictionary<string, dynamic> outputObject = new Dictionary<string, dynamic> { };

            var analyzerPackagesPath = "/Users/vincent/Desktop/EA Thesis/acr-static-analysis-code/nuget_packages.txt";
            var analyzerPackages = File.ReadAllLines(analyzerPackagesPath);
            var repo = new LocalPackageRepository("/Users/vincent/Desktop/EA Thesis/acr-static-analysis-code/nuget_analyzer_packages");
            IQueryable<IPackage> installedPackages = repo.GetPackages();
            List<IPackage> installedAnalyzerPackages = new List<IPackage>();
            foreach (IPackage package in installedPackages)
            {
                var index = Array.IndexOf(analyzerPackages, package.Id.ToString());
                if (index > -1)
                {
                    installedAnalyzerPackages.Add(package);
                }
            }
            Console.WriteLine($"Number of analyzer packages: {installedAnalyzerPackages.Count()}");
            OutputGraph(repo, analyzerPackages, installedAnalyzerPackages, 0, outputObject);
            
            String outputObjectJson = JsonConvert.SerializeObject(outputObject);
            File.WriteAllText("/Users/vincent/Desktop/EA Thesis/acr-static-analysis-code/nuget_deps.json", outputObjectJson);
        }


        static void OutputGraph(LocalPackageRepository repository, string [] analyzerPackages, IEnumerable<IPackage> packages, int depth,
            dynamic outputObject
            )
        {

            foreach (IPackage package in packages)
            {
                if (package == null)
                {
                    Console.WriteLine($"{new string(' ', depth)}Empty package");
                    continue;
                }

                Console.WriteLine($"{new string(' ', depth)}{package.Id} v{package.Version}");
                String packageIDandVersion = package.Id + "__" + package.Version;
                outputObject[packageIDandVersion] = new Dictionary<string, dynamic> { };

                IList<IPackage> dependentPackages = new List<IPackage>();
                foreach (var dependencySet in package.DependencySets)
                {
                    foreach (var dependency in dependencySet.Dependencies)
                    {
                        if (dependency.VersionSpec == null)
                        {
                            continue;
                        }

                        var semanticString = dependency.VersionSpec.ToString();
                        semanticString = semanticString.Replace("[", string.Empty).Replace("]", string.Empty);

                        if (!SemanticVersion.TryParse(semanticString, out SemanticVersion semanticVersion))
                        {
                            continue;
                        }

                        var foundPackage = repository.FindPackage(dependency.Id, semanticVersion);
                        if (
                            foundPackage == null ||

                            // Only interested in analyzer package dependencies:
                            Array.IndexOf(analyzerPackages, foundPackage.Id.ToString()) <= -1
                        ){
                            continue;
                        }

                        dependentPackages.Add(foundPackage);
                    }
                }

                // Can be repetitive; Seems like same dependency in different DependencySets?
                dependentPackages = dependentPackages.Distinct().ToList();

                OutputGraph(repository, analyzerPackages, dependentPackages, depth + 3, outputObject[packageIDandVersion]);
            }
        }
    }
}
