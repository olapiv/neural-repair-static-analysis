using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Dynamic;
using System.IO;
using System.Text;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Text;
using Microsoft.VisualBasic.CompilerServices;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace SourceCodeTokenizer
{
    class Pipeline
    {

        public string inputPath;
        public string outputPath;
        public PythonDataItem pythonDataItem;
        public string diffActionType;
        public SyntaxTree prevFileAst;

        // Creating map of {someVarName: VAR0}
        public Dictionary<string, string> zeroIndexedVariableNameMap = new Dictionary<string, string>();
        public int targetLineStart = -1;
        public int targetLineEnd = -1;
        public const int NUM_INPUT_TOKENS = 50;

        public Pipeline(string inputPath, string outputPath)
        {
            this.inputPath = inputPath;
            this.outputPath = outputPath;

            using (StreamReader sr = new StreamReader(this.inputPath))
            {
                string json = sr.ReadToEnd();
                this.pythonDataItem = JsonConvert.DeserializeObject<PythonDataItem>(json);
            }

            // For convenience
            this.diffActionType = this.pythonDataItem.ParsedDiff.ActionType;

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            string pathToFile = string.Format("{0}/submodule_repos_to_analyze/{1}/{2}", solutionPath, this.pythonDataItem.Repo, this.pythonDataItem.FilePath);
            using (StreamReader sr = new StreamReader(pathToFile))
            {
                this.prevFileAst = CSharpSyntaxTree.ParseText(sr.ReadToEnd());
            }

            this.CalculateTargetLineRange();
        }


        private void CalculateTargetLineRange()
        {
            IEnumerable<SyntaxToken> updatedCodeChunkBlockStmtTokensIEnum = Enumerable.Empty<SyntaxToken>();

            // No output with "REMOVE"
            if (this.diffActionType != "REMOVE")
            {
                if (this.diffActionType == "REPLACE")
                {
                    ReplaceAction typedParsedDiff = ((JObject)this.pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                    this.targetLineStart = typedParsedDiff.SourceLocations.First();
                    this.targetLineEnd = this.targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
                }
                else if (this.diffActionType == "ADD")
                {
                    AddAction typedParsedDiff = ((JObject)this.pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                    this.targetLineStart = typedParsedDiff.PreviousSourceLocation + 1;
                    this.targetLineEnd = this.targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
                }
            }
        }

        // TODO: Refactor this (too many functionalities)
        public static String[] AddTriviaToTokens(SyntaxToken[] syntaxTokens)
        {
            List<String> tokensAndTriviaInLineSpan = new List<String>();
            foreach (var token in syntaxTokens)
            {
                foreach (var leadingTrivia in token.LeadingTrivia)
                    tokensAndTriviaInLineSpan.Add(leadingTrivia.Kind().ToString());

                tokensAndTriviaInLineSpan.Add(token.ToString());

                // Trivia can only be leading or trailing; it is not both leading for
                // one token and trailing for another
                foreach (var trailingTrivia in token.TrailingTrivia)
                {
                    tokensAndTriviaInLineSpan.Add(trailingTrivia.Kind().ToString());
                }
            }

            return tokensAndTriviaInLineSpan.ToArray();
        }

        private SyntaxToken[] ApplyAndUpdateIndexVariableNames(IEnumerable<SyntaxToken> syntaxTokenArray)
        {

            List<SyntaxToken> newSyntaxTokenArray = new List<SyntaxToken>();
            foreach (var originalSyntaxToken in syntaxTokenArray)
            {

                if (!originalSyntaxToken.IsKind(SyntaxKind.IdentifierToken))
                {
                    newSyntaxTokenArray.Add(originalSyntaxToken);
                    continue;
                }

                var tokenName = originalSyntaxToken.ValueText;

                if (tokenName.StartsWith("VAR"))
                {
                    // Already have indexed this token (should not happen)
                    newSyntaxTokenArray.Add(originalSyntaxToken);
                    continue;
                }

                string newTokenName;
                if (this.zeroIndexedVariableNameMap.ContainsKey(tokenName))
                {
                    // Already have this saved in dict
                    newTokenName = this.zeroIndexedVariableNameMap[tokenName];
                }
                else
                {
                    newTokenName = "VAR" + this.zeroIndexedVariableNameMap.Count;
                    this.zeroIndexedVariableNameMap[tokenName] = newTokenName;

                    //Console.WriteLine($"" +
                    //    $"New zero-index var; " +
                    //    $"tokenName: {tokenName}; " +
                    //    $"Kind: {originalSyntaxToken.Kind()}"
                    //);

                }
                var newIdentifier = SyntaxFactory.Identifier(newTokenName);
                newIdentifier = newIdentifier.WithLeadingTrivia(originalSyntaxToken.LeadingTrivia);
                newIdentifier = newIdentifier.WithTrailingTrivia(originalSyntaxToken.TrailingTrivia);

                newSyntaxTokenArray.Add(newIdentifier);

            }

            return newSyntaxTokenArray.ToArray();
        }

        private void TokenizeDiagnosticMessage()
        {
            // Tokenize DiagnosticMessage

            foreach (var diag in this.pythonDataItem.DiagnosticOccurances)
            {
                diag.TokenizedMessage = new List<string>();
                foreach (var wordToken in diag.Message.Split(" "))
                {
                    // DiagnosticMessage contains variable name
                    if (wordToken.StartsWith("'") && wordToken.EndsWith("'"))
                    {
                        var wordTokenCore = wordToken.Remove(0, 1);
                        wordTokenCore = wordTokenCore.Remove(wordTokenCore.Length - 1, 1);

                        // Could also be that variable name is outside of scope - not worth
                        // indexing those, otherwise we have VAR-1000, etc.
                        if (this.zeroIndexedVariableNameMap.ContainsKey(wordTokenCore))
                        {
                            var wordTokenIndexed = this.zeroIndexedVariableNameMap[wordTokenCore];
                            diag.TokenizedMessage.Add(wordTokenIndexed);
                        }
                        else
                        {
                            // Can be difficult to find in map (e.g. 'this[]')
                            Console.WriteLine($"Weird token! : {wordTokenCore}");
                            diag.TokenizedMessage.Add($"UNKNOWN: {wordTokenCore}");
                        }
                    }
                    else
                    {
                        foreach (var splitWordToken in Regex.Split(wordToken, @"(?=[.!?\\-])|(?<=[.!?\\-])").ToList())
                        {
                            if (splitWordToken != "")
                                diag.TokenizedMessage.Add(splitWordToken.ToLower());
                        }
                    }
                }
            }
        }

        private void ProcessDiff()
        {

            // Tokenize source side of diff with file context

            var (startTokenIndex, endTokenIndex) = Utils.GetTokenRangeByLineSpan(
                this.prevFileAst.GetRoot(),
                (int)this.pythonDataItem.RequiredLinesStart,
                (int)this.pythonDataItem.RequiredLinesEnd
            );

            var numTokens = (endTokenIndex - startTokenIndex) + 1;
            if (numTokens > Pipeline.NUM_INPUT_TOKENS)
            {
                throw new Exception($"Diff is too large; numTokens: {numTokens}");
            }
            var missingTokens = Pipeline.NUM_INPUT_TOKENS - numTokens;

            // TODO: Add Error tokens

            // All tokens in diff of previous file without context
            var prevCodeChunkBlockStmtTokensList = Utils.GetTokensByLineSpan(
                this.prevFileAst.GetRoot(),
                (int)this.pythonDataItem.RequiredLinesStart,
                (int)this.pythonDataItem.RequiredLinesEnd
            ).ToList();

            var allDescendentTokens = this.prevFileAst.GetRoot().DescendantTokens().ToList();

            prevCodeChunkBlockStmtTokensList = Utils.AddContextTokensToListOfTokens(
                prevCodeChunkBlockStmtTokensList,
                allDescendentTokens,
                startTokenIndex,
                endTokenIndex,
                missingTokens
            );

            // -------
            // Get updated file data

            var updatedFile = Utils.ApplyParsedDiff(this.pythonDataItem.ParsedDiff, this.prevFileAst.GetText());
            var updatedFileAst = CSharpSyntaxTree.ParseText(updatedFile);

            // -------

            // TODO: Use this to check for useless files (like in original file)
            var prevFileTokens = this.prevFileAst.GetRoot().DescendantTokens().ToList();
            var updatedFileTokens = updatedFileAst.GetRoot().DescendantTokens().ToList();
            var prevTokenIndex = new TokenIndex(prevFileTokens);
            var updatedTokenIndex = new TokenIndex(updatedFileTokens);

            // -------
            // Tokenize all target lines from diff

            IEnumerable<SyntaxToken> updatedCodeChunkBlockStmtTokensIEnum = Enumerable.Empty<SyntaxToken>();

            // No output with "REMOVE"
            if (this.diffActionType != "REMOVE")
            {
                updatedCodeChunkBlockStmtTokensIEnum = Utils.GetTokensByLineSpan(
                    updatedFileAst.GetRoot(),
                    this.targetLineStart,
                    this.targetLineEnd
                );
            }

            var updatedCodeChunkBlockStmtTokens = updatedCodeChunkBlockStmtTokensIEnum.ToArray();

            // -------
            // Zero-index all variable names

            var prevCodeChunkBlockStmtTokens = prevCodeChunkBlockStmtTokensList.ToArray();
            var allTokens = new SyntaxToken[updatedCodeChunkBlockStmtTokens.Length + prevCodeChunkBlockStmtTokens.Length];
            updatedCodeChunkBlockStmtTokens.CopyTo(allTokens, 0);
            prevCodeChunkBlockStmtTokens.CopyTo(allTokens, updatedCodeChunkBlockStmtTokens.Length);

            allTokens = ApplyAndUpdateIndexVariableNames(allTokens);
            prevCodeChunkBlockStmtTokens = ApplyAndUpdateIndexVariableNames(prevCodeChunkBlockStmtTokens);
            updatedCodeChunkBlockStmtTokens = ApplyAndUpdateIndexVariableNames(updatedCodeChunkBlockStmtTokens);

            // -------
            // firstLinePrev/firstLineNew are offsets for other indices

            // Problem if first variable has been zero-indexed (position is then 0)
            // TODO: Use ReplaceNodes() for zero-indexing vars, so that position is kept (they have position 0)

            var firstLinePrev = 0;
            var firstLineNew = 0;

            if (prevCodeChunkBlockStmtTokens.Count() != 0)
                firstLinePrev = prevCodeChunkBlockStmtTokens.First().GetLocation().GetLineSpan().StartLinePosition.Line;

            if (updatedCodeChunkBlockStmtTokens.Count() != 0)
                firstLineNew = updatedCodeChunkBlockStmtTokens.First().GetLocation().GetLineSpan().StartLinePosition.Line;

            // -------
            // Generate finished list of tokens in the change including formatting
            // Does not work though if only trivia in span (no tokens); See next section for fix.

            var prevCodeChunkBlockStmtTextTokens = AddTriviaToTokens(prevCodeChunkBlockStmtTokens);
            var updatedCodeChunkBlockStmtTextTokens = AddTriviaToTokens(updatedCodeChunkBlockStmtTokens);

            // -------
            // In case that all added lines for ADD/REPLACE are trivia; In this case,
            // there is no token to get Leading/Trailing Trivia from

            if ((this.diffActionType == "REPLACE") || (this.diffActionType == "ADD"))
            {
                if (updatedCodeChunkBlockStmtTextTokens.Count() == 0)
                {
                    Console.WriteLine($"Empty updatedCodeChunkBlockStmtTextTokens! Adding trivia without tokens then.");

                    var updatedCodeChunkBlockTrivia = Utils.GetTriviaByLineSpan(
                        updatedFileAst.GetRoot(),
                        this.targetLineStart,
                        this.targetLineEnd
                    );
                    firstLineNew = updatedCodeChunkBlockTrivia.First().GetLocation().GetLineSpan().StartLinePosition.Line;

                    updatedCodeChunkBlockStmtTextTokens = updatedCodeChunkBlockTrivia.Select(trivia => trivia.Kind().ToString()).ToArray();
                }
            }

            Console.WriteLine($"firstLinePrev : {firstLinePrev}");
            Console.WriteLine($"firstLineNew : {firstLineNew}");

            // -------

            this.TokenizeDiagnosticMessage();

            // -------
            // Write all calculated data to JSONObject

            if (this.diffActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)this.pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;

                // typedParsedDiff.SourceLocations = typedParsedDiff.SourceLocations.Select(x => x - firstLinePrev).ToList().ToArray();

                typedParsedDiff.SourceLocations.ToList().ForEach(d => d -= firstLinePrev);
                this.pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }
            else if (this.diffActionType == "REMOVE")
            {
                // Nothing to tokenize, only change offsets
                RemoveAction typedParsedDiff = ((JObject)this.pythonDataItem.ParsedDiff.Action).ToObject<RemoveAction>();
                typedParsedDiff.SourceLocationStart -= firstLinePrev;
                typedParsedDiff.SourceLocationEnd -= firstLinePrev;
                this.pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }
            else if (this.diffActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)this.pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
                typedParsedDiff.PreviousSourceLocation -= firstLinePrev;
                this.pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }

            this.pythonDataItem.TokenizedFileContext = prevCodeChunkBlockStmtTextTokens.ToList();
            this.pythonDataItem.DiagnosticOccurances.ForEach(d => d.Line -= firstLinePrev);

            return;
        }

        private void SaveResults()
        {
            this.pythonDataItem.RemoveOldData();
            var newDataItem = JsonConvert.SerializeObject(
                this.pythonDataItem,
                Formatting.Indented,
                new JsonSerializerSettings
                {
                    NullValueHandling = NullValueHandling.Ignore
                }
            );

            var newFilename = Path.GetFileName(this.inputPath);
            var newFilepath = Path.Combine(this.outputPath, newFilename);
            System.IO.File.WriteAllText(newFilepath, newDataItem);
        }

        public void Run()
        {
            try
            {
                this.ProcessDiff();
            }
            catch (Exception e)
            {
                Console.WriteLine($"e: {e}");
                System.Environment.Exit(1);
            }
            this.SaveResults();
        }

        private static readonly HashSet<string> keywords =
            new HashSet<string>() {"VAR0", "int", "long", "string", "float", "LITERAL", "var"};

        private static bool IsValidCodeChunkTokens(IEnumerable<string> tokens)
        {
            var validTokenCount = tokens.Count(token => !keywords.Contains(token) && !token.All(char.IsPunctuation));

            return validTokenCount > 0;
        }
    }

}
