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
        Previously:
          input_file: commit_data.jsonl
          output_file: github_commits.dataset.jsonl
          grammar_file: grammar.full.json

        Single entry (one line) in commit_data.jsonl:
          entry = OrderedDict(id=revision_id, prev_file=prev_file_content, updated_file=updated_file_content)

        Problem:
            - How to parse diagnostic message? e.g. 'Replace DateTime usage with DateTimeOffset'
            - Also need to tokenize all ParsedDiff.Action.TargetLines

        TODO Change in refining_dataset.py:
            - Add 'requiredLinesStart' and 'requiredLinesEnd'
            - Keep 'FileContext' for now for basic comparison
            - 

        New input:
            - folder with all json files (output is same)
            - grammar file (?)

        Other input: <grammar_file>

        */

        private static void Main(string[] args)
        {

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            string refined_dataset_path = Path.Combine(solutionPath, "refined_dataset");
            Console.WriteLine($"refined_dataset_path: {refined_dataset_path}");

            Pipeline.DumpRevisionDataForNeuralTraining(
                refined_dataset_path,
                "path-to-grammar_file"
            );
            
        }
    }
}
