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
            this.pathToAssembly = pathToAssembly;
            AppDomain.CurrentDomain.AssemblyResolve += CurrentDomain_AssemblyResolve;
            this.assembly = Assembly.LoadFrom(pathToAssembly);

            this.analyzers = new List<DiagnosticAnalyzer>();
            this.codeFixers = new List<CodeFixProvider>();
            this.codeRefactorings = new List<CodeRefactoringProvider>();

            this.diagnosticsCSV = new List<DiagnosticInfoAsCSV>();
        }

        private Assembly CurrentDomain_AssemblyResolve(object sender, ResolveEventArgs args)
        {
            var assemblyName = args.Name.Split(',').First();
            if (assemblyName.EndsWith(".resources", StringComparison.InvariantCultureIgnoreCase))
                return null;

            var assemblyLookingFor = assemblyName + ".dll";

            var currentAssemblyDir = Path.GetDirectoryName(pathToAssembly);
            var allFilesCurrent = Directory.GetFiles(currentAssemblyDir, assemblyLookingFor, SearchOption.AllDirectories);
            if (allFilesCurrent.Any())
            {
                return Assembly.LoadFrom(allFilesCurrent.First());
            }


            var relevantDir = Path.Combine(Directory.GetCurrentDirectory(), "nuget_analyzer_packages");
            var allDirs = Directory.GetDirectories(relevantDir).Where(dir => dir.ToLower().Contains(assemblyName.ToLower()));
            foreach ( var dir in allDirs)
            {
                var allFiles = Directory.GetFiles(relevantDir, assemblyLookingFor, SearchOption.AllDirectories);

                if (allFiles.Any())
                {
                    return Assembly.LoadFrom(allFiles.First());
                }
            }

            Console.WriteLine($"args.Name: {args.Name}");
            Console.WriteLine($"args.RequestingAssembly: {args.RequestingAssembly.FullName}");
            return null;

            // throw new NotImplementedException();
        }

        public String pathToAssembly;
        public Assembly assembly;
        public List<DiagnosticAnalyzer> analyzers;
        public List<CodeFixProvider> codeFixers;
        public List<CodeRefactoringProvider> codeRefactorings;
        public List<DiagnosticInfoAsCSV> diagnosticsCSV;

        public void LoadCodeFixProviders()
        {
            this.codeFixers.Clear();

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

                this.codeFixers.Add(codeFixer);
            }
            Console.WriteLine($"Number of CodeFixProviders: {this.codeFixers.Count}");
        }

        public void LoadDiagnosticAnalyzers()
        {

            this.analyzers.Clear();

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

                this.analyzers.Add(analyzer);
            }
            Console.WriteLine($"Number of DiagnosticAnalyzers: {this.analyzers.Count}");
        }

        public void LoadCodeRefactoringProviders()
        {

            this.codeRefactorings.Clear();

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

                this.codeRefactorings.Add(codeRefactoring);
            }
            Console.WriteLine($"Number of CodeRefactoringProvider: {this.codeRefactorings.Count}");

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

            foreach (DiagnosticAnalyzer analyzer in analyzers)
            {

                foreach (DiagnosticDescriptor descriptor in analyzer.SupportedDiagnostics)
                {
                    var title = descriptor.Title.ToString();
                    var description = descriptor.Description.ToString();

                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(
                            packageName,
                            assembly,
                            "DIAGNOSTIC_ANALYZER",
                            descriptor.Id.ToString(),
                            title,
                            description,
                            descriptor.DefaultSeverity.ToString(),
                            descriptor.Category,
                            String.Join(", ", descriptor.CustomTags.ToArray())
                        )
                    );
                };

            };

            foreach (CodeFixProvider codeFixer in codeFixers)
            {

                var FixAllDiagnosticIDs = Enumerable.Empty<String>();
                var supportedScopes = "";
                var fixAllProvider = codeFixer.GetFixAllProvider();
                if (fixAllProvider != null) {
                    FixAllDiagnosticIDs = fixAllProvider.GetSupportedFixAllDiagnosticIds(codeFixer);
                    supportedScopes = String.Join(", ", fixAllProvider.GetSupportedFixAllScopes().ToArray());
                }

                foreach (String fixableDiagnosticID in codeFixer.FixableDiagnosticIds)
                {
                    
                    this.diagnosticsCSV.Add(
                        new DiagnosticInfoAsCSV(
                            packageName,
                            assembly,
                            "CODEFIX_PROVIDER",
                            fixableDiagnosticID,
                            containsFixAllProvider: FixAllDiagnosticIDs.Contains(fixableDiagnosticID).ToString(),
                            fixAllProviderSupportedScopes: supportedScopes
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
                        refactoringName: codeRefactoring.GetType().Name
                    )
                );
            };
        }

        public void AppendToCSV(String pathToCSV)
        {

            var config = new CsvConfiguration(CultureInfo.CurrentCulture)
            {
                HasHeaderRecord = false
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
