using System;
using System.Linq;
using System.Collections.Immutable;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.Diagnostics;
using System.Reflection;
using CsvHelper;
using CsvHelper.Configuration;
using System.IO;
using System.Globalization;


namespace InfoExtractor
{
    public class AssemblyParser
    {
        public AssemblyParser(String pathToAssembly)
        {
            this.assembly = Assembly.LoadFrom(pathToAssembly);
            this.analyzers = LoadDiagnosticAnalyzers();
            this.codeFixers = LoadCodeFixProviders();
        }

        public Assembly assembly;
        public List<DiagnosticAnalyzer> analyzers;
        public List<CodeFixProvider> codeFixers;
        public List<DiagnosticInfoAsCSV> diagnosticsCSV;

        public List<CodeFixProvider> LoadCodeFixProviders()
        {
            Console.WriteLine("Loading code fixes!");
            List<CodeFixProvider> codeFixers = new List<CodeFixProvider>();

            foreach (System.Reflection.TypeInfo typeInfo in assembly.DefinedTypes)
            {
                if (typeInfo.IsAbstract
                    || !typeInfo.IsSubclassOf(typeof(CodeFixProvider)))
                {
                    continue;
                }

                ExportCodeFixProviderAttribute attribute = typeInfo.GetCustomAttribute<ExportCodeFixProviderAttribute>();
                if (attribute == null)
                {
                    Console.WriteLine("No attribute!");
                    continue;
                }

                if (!attribute.Languages.Contains("C#"))
                {
                    Console.WriteLine("Does not contain C#!");
                    continue;
                }

                CodeFixProvider codeFixer = CreateInstanceAndCatchIfThrows<CodeFixProvider>(typeInfo);
                if (codeFixer == null)
                {
                    Console.WriteLine("No coder fixer!");
                    continue;
                }

                codeFixers.Add(codeFixer);
            }
            return codeFixers;
        }

        public List<DiagnosticAnalyzer> LoadDiagnosticAnalyzers()
        {
            Console.WriteLine("Loading diagnostics!");
            List<DiagnosticAnalyzer> analyzers = new List<DiagnosticAnalyzer>();

            foreach (System.Reflection.TypeInfo typeInfo in assembly.DefinedTypes)
            {
                if (typeInfo.IsAbstract
                    || !typeInfo.IsSubclassOf(typeof(DiagnosticAnalyzer)))
                {
                    continue;
                }

                DiagnosticAnalyzerAttribute attribute = typeInfo.GetCustomAttribute<DiagnosticAnalyzerAttribute>();
                if (attribute == null)
                {
                    Console.WriteLine("No attribute!");
                    continue;
                }

                if (!attribute.Languages.Contains("C#"))
                {
                    Console.WriteLine("Does not contain C#!");
                    continue;
                }

                DiagnosticAnalyzer analyzer = CreateInstanceAndCatchIfThrows<DiagnosticAnalyzer>(typeInfo);
                if (analyzer == null)
                {
                    Console.WriteLine("No analyzer!");
                    continue;
                }

                analyzers.Add(analyzer);
            }
            return analyzers;
        }


        private static T CreateInstanceAndCatchIfThrows<T>(System.Reflection.TypeInfo typeInfo)
        {
            try
            {
                return (T)Activator.CreateInstance(typeInfo.AsType());
            }
            catch (TargetInvocationException ex)
            {
                Console.WriteLine($"Cannot create instance of type '{typeInfo.FullName}'");
                Console.WriteLine(ex.ToString());
            }

            return default;
        }

        public void GenerateCSVRepresentations(String packageName)
        {
            this.diagnosticsCSV = new List<DiagnosticInfoAsCSV>();

            foreach (DiagnosticAnalyzer analyzer in analyzers)
            {
                foreach (DiagnosticDescriptor descriptor in analyzer.SupportedDiagnostics)
                {
                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(packageName, assembly, "DIAGNOSTIC_ANALYZER", descriptor.Id.ToString())
                    );
                };
            };

            foreach (CodeFixProvider codeFixer in codeFixers)
            {
                foreach (String fixableDiagnosticID in codeFixer.FixableDiagnosticIds)
                {
                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(packageName, assembly, "CODEFIX_PROVIDER", fixableDiagnosticID)
                    );
                }
            };
        }

        public void WriteToCSV(String pathToCSV, Boolean newFile)
        {
            if (newFile)
            {
                using (var writer = new StreamWriter(pathToCSV))
                using (var csv = new CsvWriter(writer, CultureInfo.InvariantCulture))
                {
                    csv.WriteRecords(this.diagnosticsCSV);
                }
            }
            {
                // Append to file
                var config = new CsvConfiguration(CultureInfo.InvariantCulture)
                {
                    // Don't write the header again.
                    HasHeaderRecord = false,
                };
                using (var stream = File.Open(pathToCSV, FileMode.Append))
                using (var writer = new StreamWriter(stream))
                using (var csv = new CsvWriter(writer, config))
                {
                    csv.WriteRecords(this.diagnosticsCSV);
                }

            }
        }
    }
}
