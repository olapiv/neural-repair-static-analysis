using System;
using System.IO;
using System.Globalization;
using System.Threading;
using System.Reflection;
using System.Collections.Generic;
using CsvHelper;
using CsvHelper.Configuration;

namespace InfoExtractor
{
    class MainClass
    {
        public static List<String> packageNamesToExclude = new List<string>()
        {
            "AnalyzerApi.1.1.4.21",  // Requires System runtime, which is not provided by Mono
            "Augurk.CSharpAnalyzer.0.1.0",  // Mac-specific problems
            "Autofac.6.1.0"  // Expected class 'System.IAsyncDisposable' in assembly 'System.Runtime'
        };

        public static void Main(string[] args)
        {
            String pathToAnalyzerPackage = args[0];
            String pathToCSV = args[1];
            String newCSV = args[2];

            CultureInfo ci = new CultureInfo("en-US");
            Thread.CurrentThread.CurrentCulture = ci;
            Thread.CurrentThread.CurrentUICulture = ci;

            Boolean newCSVBool = newCSV.Equals("True");
            if (newCSVBool)
            {
                System.IO.File.WriteAllText(pathToCSV, string.Empty);

                using (StreamWriter sw = new StreamWriter(pathToCSV))
                {
                    using (CsvWriter writer = new CsvWriter(sw, new CsvConfiguration(CultureInfo.CurrentCulture)))
                    {
                        writer.WriteHeader<DiagnosticInfoAsCSV>();
                        writer.NextRecord();
                    }
                }
            }

            String packageName = new DirectoryInfo(pathToAnalyzerPackage).Name;
            Console.WriteLine($"packageName: {packageName}");

            if (MainClass.packageNamesToExclude.Contains(packageName))
                System.Environment.Exit(0);

            var successfulAssemblyNames = new List<String>();

            AssemblyParser assemblyParser;
            foreach (String assemblyPath in Directory.EnumerateFiles(pathToAnalyzerPackage, "*.dll", SearchOption.AllDirectories))
            {
                
                String assemblyFilename = Path.GetFileName(assemblyPath);
                Console.WriteLine("assemblyFilename: {0}", assemblyFilename);

                // Same assembly file may be available for different target frameworks; avoid duplications
                if (successfulAssemblyNames.Contains(assemblyFilename))
                {
                    Console.WriteLine("assemblyFilename already handled successfully");
                    continue;
                }

                var successful = true;

                try
                {
                    assemblyParser = new AssemblyParser(assemblyPath);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception instantiating AssemblyParser: {ex}");
                    continue;
                }

                try
                {
                    assemblyParser.LoadDefinedTypes();
                } catch (ReflectionTypeLoadException)
                {
                    continue;
                }

                try
                {
                    assemblyParser.LoadDiagnosticAnalyzers();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadDiagnosticAnalyzers: {ex}");
                    successful = false;
                }

                try
                {
                    assemblyParser.LoadCodeFixProviders();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadCodeFixProviders: {ex}");
                    successful = false;
                }

                try
                {
                    assemblyParser.LoadCodeRefactoringProviders();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadCodeRefactoringProviders: {ex}");
                    successful = false;
                }

                if (successful)
                    successfulAssemblyNames.Add(assemblyFilename);


                // AssemblyParser assemblyParser = new AssemblyParser(assemblyPath);
                assemblyParser.GenerateCSVRepresentations(packageName);
                assemblyParser.AppendToCSV(pathToCSV);
                newCSVBool = false;
            }
        }
    }
}