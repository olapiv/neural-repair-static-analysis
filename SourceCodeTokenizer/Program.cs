using Microsoft.CodeAnalysis;
using System;
using System.IO;
using System.Linq;


namespace SourceCodeTokenizer
{
    class Program
    {

        private static void Main(string[] args)
        {

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            string unified_dataset_path = Path.Combine(solutionPath, "unified_dataset");
            string tokenized_dataset_path = Path.Combine(solutionPath, "tokenized_dataset");
            Directory.CreateDirectory(tokenized_dataset_path);  // Creates if not exists

            Console.WriteLine($"unified_dataset_path: {unified_dataset_path}");

            string[] refinedJSONpaths = Directory.GetFiles(unified_dataset_path, "*.json",
                             SearchOption.TopDirectoryOnly);

            Console.WriteLine($"Number JSON files: {refinedJSONpaths.Count()}");
            
            foreach (var JSONpath in refinedJSONpaths)
            {
                Console.WriteLine($"JSONpath: {JSONpath}");

                var datapoint = new Pipeline(
                    JSONpath,
                    tokenized_dataset_path
                );

                datapoint.Run();
            }
            
        }
    }
}
