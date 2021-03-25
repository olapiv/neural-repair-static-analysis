using System;
using System.Linq;
using System.Collections.Immutable;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.Diagnostics;
using System.Reflection;
using CsvHelper;
using System.IO;
using System.Globalization;


namespace InfoExtractor
{
    public class AssemblyParser
    {
        public AssemblyParser(String pathToAssembly)
        {
            assembly = Assembly.LoadFrom(pathToAssembly);
            analyzers = LoadDiagnosticAnalyzers();
            codeFixers = LoadCodeFixProviders();
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
            List<DiagnosticAnalyzer> analyzers = new List<DiagnosticAnalyzer>(); ;

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

        public void GenerateCSVRepresentations()
        {
            foreach (DiagnosticAnalyzer analyzer in analyzers)
            {
                foreach (DiagnosticDescriptor descriptor in analyzer.SupportedDiagnostics)
                {
                    diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(assembly, "DiagnosticAnalyzer", descriptor.Id.ToString())
                    );
                };
            };

            foreach (CodeFixProvider codeFixer in codeFixers)
            {
                foreach (String fixableDiagnosticID in codeFixer.FixableDiagnosticIds)
                {
                    diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(assembly, "CodeFixProvider", fixableDiagnosticID)
                    );
                }
            };
        }

        public void WriteToCSV(String pathToCSV)
        {
            // Write to a file.
            using (var writer = new StreamWriter(pathToCSV))
            using (var csv = new CsvWriter(writer, CultureInfo.InvariantCulture))
            {
                csv.WriteRecords(diagnosticsCSV);
            }
        }
    }
}
