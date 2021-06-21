using System;
using System.IO;
using System.Globalization;
using System.Threading;

namespace InfoExtractor
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            // ../../nuget_analyzer_packages
            // ../../analyzer_package_details_new.csv
            // True
            Console.WriteLine($"------------------------------------------");
            String pathAllNugetAnalyzers = args[0];
            String pathToCSV = args[1];
            String newCSV = args[2];
            Boolean newCSVBool = newCSV.Equals("True");

            CultureInfo ci = new CultureInfo("en-US");
            Thread.CurrentThread.CurrentCulture = ci;
            Thread.CurrentThread.CurrentUICulture = ci;

            Console.WriteLine($"pathToAnalyzerPackage: {pathAllNugetAnalyzers}");
            
            AssemblyParser assemblyParser;
            foreach (String nugetPath in Directory.EnumerateDirectories(pathAllNugetAnalyzers))
            {

                String packageName = new DirectoryInfo(nugetPath).Name;
                Console.WriteLine($"    packageName: {packageName}");

                foreach (String assemblyPath in Directory.EnumerateFiles(nugetPath, "*.dll", SearchOption.AllDirectories))
                {
                    String assemblyFilename = Path.GetFileName(assemblyPath);
                    Console.WriteLine("assemblyFilename: {0}", assemblyFilename);

                    try
                    {
                        assemblyParser = new AssemblyParser(assemblyPath);
                    }
                    catch (Exception ex)
                    {
                        if (ex is System.BadImageFormatException){
                            Console.WriteLine("System.BadImageFormatException");
                            continue;
                        } else if (ex is System.Reflection.ReflectionTypeLoadException){
                            Console.WriteLine("System.Reflection.ReflectionTypeLoadException");
                            continue;
                        }
                        continue;
                    }

                    assemblyParser.GenerateCSVRepresentations(packageName);
                    assemblyParser.WriteToCSV(pathToCSV, newCSVBool);
                    newCSVBool = false;
                }
                // System.Environment.Exit(1);
            }
        }
    }
}
