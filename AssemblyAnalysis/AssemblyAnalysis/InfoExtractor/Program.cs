using System;
using System.IO;

namespace InfoExtractor
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            Console.WriteLine("Starting!");

            String pathToAnalyzerPackage = args[0];
            String pathToCSV = args[1];
            String packageName = new DirectoryInfo(pathToAnalyzerPackage).Name;
            Console.WriteLine("packageName: {0}", packageName);
            Boolean newFile = true;
            foreach (String assemblyPath in Directory.EnumerateFiles(pathToAnalyzerPackage, "*.dll", SearchOption.AllDirectories))
            {
                Console.WriteLine("assemblyPath: {0}", assemblyPath);
                AssemblyParser assemblyParser = new AssemblyParser(assemblyPath);
                assemblyParser.GenerateCSVRepresentations(packageName);
                assemblyParser.WriteToCSV(pathToCSV, newFile);
                newFile = false;
            }
            Console.WriteLine("Finished!");
        }
    }
}
