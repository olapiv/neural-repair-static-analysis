using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Text;
using Mono.Options;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using DocoptNet;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace SourceCodeTokenizer
{
    class Program
    {

        /*
        Original input:
          input_file: commit_data.jsonl
          output_file: github_commits.dataset.jsonl
          grammar_file: grammar.full.json

        whereby, single entry (one line) in commit_data.jsonl:
          entry = OrderedDict(id=revision_id, prev_file=prev_file_content, updated_file=updated_file_content)

        New input:
            - folder with all json files (output is same)
            - grammar file (?)
        */

        private static void Main(string[] args)
        {

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            string unified_dataset_path = Path.Combine(solutionPath, "unified_dataset");
            string tokenized_dataset_path = Path.Combine(solutionPath, "tokenized_dataset");
            Directory.CreateDirectory(tokenized_dataset_path);  // Creates if not exists

            Console.WriteLine($"unified_dataset_path: {unified_dataset_path}");

            string[] refinedJSONpaths = Directory.GetFiles(unified_dataset_path, "*.json",
                             SearchOption.TopDirectoryOnly);

            Console.WriteLine($"refinedJSONpaths.Count(): {refinedJSONpaths.Count()}");
            Console.WriteLine($"refinedJSONpaths.First(): {refinedJSONpaths.First()}");
            
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
