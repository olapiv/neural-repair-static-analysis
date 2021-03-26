using System;
using System.IO;

namespace InfoExtractor
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            String pathToAnalyzerPackage = args[0];
            String pathToCSV = args[1];
            String newCSV = args[2];
            Boolean newCSVBool = newCSV.Equals("True");
            String packageName = new DirectoryInfo(pathToAnalyzerPackage).Name;
            Console.WriteLine($"packageName: {packageName}");
            foreach (String assemblyPath in Directory.EnumerateFiles(pathToAnalyzerPackage, "*.dll", SearchOption.AllDirectories))
            {
                String assemblyFilename = Path.GetFileName(assemblyPath);
                Console.WriteLine("assemblyFilename: {0}", assemblyFilename);
                AssemblyParser assemblyParser = new AssemblyParser(assemblyPath);
                assemblyParser.GenerateCSVRepresentations(packageName);
                assemblyParser.WriteToCSV(pathToCSV, newCSVBool);
                newCSVBool = false;
            }
        }
    }
}
