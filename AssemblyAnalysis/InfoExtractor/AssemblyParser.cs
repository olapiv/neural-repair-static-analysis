﻿using System;
using System.Linq;
using System.Collections.Immutable;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.CodeRefactorings;
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
            this.codeRefactorings = LoadCodeRefactoringProviders();
        }

        public Assembly assembly;
        public List<DiagnosticAnalyzer> analyzers;
        public List<CodeFixProvider> codeFixers;
        public List<CodeRefactoringProvider> codeRefactorings;
        public List<DiagnosticInfoAsCSV> diagnosticsCSV;

        public List<CodeFixProvider> LoadCodeFixProviders()
        {
            List<CodeFixProvider> codeFixers = new List<CodeFixProvider>();

            // Can throw ReflectionTypeLoadException for unkown reasons
            var assemblyTypes = assembly.DefinedTypes.ToArray();

            foreach (System.Reflection.TypeInfo typeInfo in assemblyTypes)
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
            Console.WriteLine($"Number of CodeFixProviders: {codeFixers.Count}");
            return codeFixers;
        }

        public List<DiagnosticAnalyzer> LoadDiagnosticAnalyzers()
        {
            List<DiagnosticAnalyzer> analyzers = new List<DiagnosticAnalyzer>();

            // Can throw ReflectionTypeLoadException for unkown reasons
            var assemblyTypes = assembly.DefinedTypes.ToArray();

            foreach (System.Reflection.TypeInfo typeInfo in assemblyTypes)
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
            Console.WriteLine($"Number of DiagnosticAnalyzers: {analyzers.Count}");
            return analyzers;
        }

        public List<CodeRefactoringProvider> LoadCodeRefactoringProviders()
        {
            List<CodeRefactoringProvider> codeRefactorings = new List<CodeRefactoringProvider>();

            // Can throw ReflectionTypeLoadException for unkown reasons
            var assemblyTypes = assembly.DefinedTypes.ToArray();

            foreach (System.Reflection.TypeInfo typeInfo in assemblyTypes)
            {
                if (typeInfo.IsAbstract
                    || !typeInfo.IsSubclassOf(typeof(CodeRefactoringProvider)))
                {
                    continue;
                }

                ExportCodeRefactoringProviderAttribute attribute = typeInfo.GetCustomAttribute<ExportCodeRefactoringProviderAttribute>();
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

                CodeRefactoringProvider codeRefactoring = CreateInstanceAndCatchIfThrows<CodeRefactoringProvider>(typeInfo);
                if (codeRefactoring == null)
                {
                    Console.WriteLine("No coder fixer!");
                    continue;
                }

                codeRefactorings.Add(codeRefactoring);
            }
            Console.WriteLine($"Number of CodeRefactoringProvider: {codeRefactorings.Count}");

            return codeRefactorings;
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

                    descriptor.GetType();
                    
                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(
                            packageName,
                            assembly,
                            "DIAGNOSTIC_ANALYZER",
                            descriptor.Id.ToString(),
                            descriptor.Title.ToString(),
                            descriptor.Description.ToString(),
                            descriptor.DefaultSeverity.ToString(),
                            descriptor.Category,
                            String.Join(", ", descriptor.CustomTags.ToArray())
                        )
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
                var fixAllProvider = codeFixer.GetFixAllProvider();
                if (fixAllProvider == null)
                    continue;
                foreach (String FixAllDiagnosticID in fixAllProvider.GetSupportedFixAllDiagnosticIds(codeFixer))
                {
                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(
                            packageName,
                            assembly,
                            "FIX_ALL_PROVIDER",
                            FixAllDiagnosticID
                        )
                    );
                }
            };

            foreach (CodeRefactoringProvider codeRefactoring in codeRefactorings)
            {

                // codeRefactoring.ToString(),              --> Gu.Analyzers.Refactoring.ParameterRefactoring
                // codeRefactoring.GetType().ToString(),    --> Gu.Analyzers.Refactoring.ParameterRefactoring
                // codeRefactoring.GetType().Name           --> ParameterRefactoring
                // codeRefactoring.GetType().FullName       --> Gu.Analyzers.Refactoring.ParameterRefactoring

                this.diagnosticsCSV.Add(
                    new DiagnosticInfoAsCSV(
                        packageName,
                        assembly,
                        "CODEREFACTORING_PROVIDER",
                        "", "","","","","",
                        codeRefactoring.GetType().Name
                    )
                );
            };
        }

        public void WriteToCSV(String pathToCSV, Boolean newFile)
        {
            if (newFile)
            {
                using (var writer = new StreamWriter(pathToCSV))
                using (var csv = new CsvWriter(writer, CultureInfo.CurrentCulture))
                {
                    csv.WriteRecords(this.diagnosticsCSV);
                }
            }
            {
                // Append to file
                var config = new CsvConfiguration(CultureInfo.CurrentCulture)
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
