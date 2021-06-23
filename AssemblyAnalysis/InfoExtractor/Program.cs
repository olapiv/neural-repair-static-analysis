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
            String pathToAnalyzerPackage = args[0];
            String pathToCSV = args[1];
            String newCSV = args[2];

            CultureInfo ci = new CultureInfo("en-US");
            Thread.CurrentThread.CurrentCulture = ci;
            Thread.CurrentThread.CurrentUICulture = ci;

            Boolean newCSVBool = newCSV.Equals("True");
            String packageName = new DirectoryInfo(pathToAnalyzerPackage).Name;
            Console.WriteLine($"packageName: {packageName}");
            AssemblyParser assemblyParser;
            foreach (String assemblyPath in Directory.EnumerateFiles(pathToAnalyzerPackage, "*.dll", SearchOption.AllDirectories))
            {
                String assemblyFilename = Path.GetFileName(assemblyPath);
                Console.WriteLine("assemblyFilename: {0}", assemblyFilename);

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
                    assemblyParser.LoadDiagnosticAnalyzers();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadDiagnosticAnalyzers: {ex}");
                }

                try
                {
                    assemblyParser.LoadCodeFixProviders();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadCodeFixProviders: {ex}");
                }

                try
                {
                    assemblyParser.LoadCodeRefactoringProviders();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Exception LoadCodeRefactoringProviders: {ex}");
                }


                // AssemblyParser assemblyParser = new AssemblyParser(assemblyPath);
                assemblyParser.GenerateCSVRepresentations(packageName);
                assemblyParser.WriteToCSV(pathToCSV, newCSVBool);
                newCSVBool = false;
            }
        }
    }
}