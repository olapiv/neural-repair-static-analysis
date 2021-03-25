using System;

namespace InfoExtractor
{
    class MainClass
    {
        public static void Main(string[] args)
        {
            Console.WriteLine("Starting!");

            String pathToAssembly = args[0];
            String pathToCSV = args[1];
            AssemblyParser assemblyParser = new AssemblyParser(pathToAssembly);
            assemblyParser.GenerateCSVRepresentations();
            assemblyParser.WriteToCSV(pathToCSV);

            Console.WriteLine("Finished!");
        }
    }
}
