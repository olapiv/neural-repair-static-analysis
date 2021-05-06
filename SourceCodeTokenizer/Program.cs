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
            Console.WriteLine($"unified_dataset_path: {unified_dataset_path}");

            Pipeline.DumpRevisionDataForNeuralTraining(
                unified_dataset_path,
                "path-to-grammar_file"
            );
            
        }
    }
}
