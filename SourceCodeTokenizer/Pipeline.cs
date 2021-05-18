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

        public static IEnumerable<SyntaxToken> GetTokensByLineSpan(SyntaxNode astNode, int startLine, int endLine)
        {

            startLine--;
            endLine--;

            var tokensInLineSpan = astNode.DescendantTokens().Where(token =>
                (
                    token.GetLocation().GetLineSpan().EndLinePosition.Line >= startLine
                    &&
                    token.GetLocation().GetLineSpan().StartLinePosition.Line <= endLine
                )
            );

            return tokensInLineSpan;
        }

        public static List<SyntaxTrivia> FlattenDescendentTrivia(List<SyntaxTrivia> triviaList, SyntaxTrivia trivia)
        {
            if (trivia.HasStructure)
            {
                var descTrivia = trivia.GetStructure().DescendantTrivia();
                if (descTrivia.Count() == 0)
                {
                    triviaList.Add(trivia);
                }
                else
                {
                    foreach (var triviaInStruct in descTrivia)
                    {
                        triviaList = FlattenDescendentTrivia(triviaList, triviaInStruct);
                    }
                }
            } else
            {
                triviaList.Add(trivia);
            }
            return triviaList;
        }

        public static IEnumerable<String> GetTriviaByLineSpan(SyntaxNode astNode, int startLine, int endLine)
        {
            startLine--;
            endLine--;

            Console.WriteLine($"astNode.DescendantTrivia().Count(): {astNode.DescendantTrivia().Count()}");
            var allDescendentTrivia = new List<SyntaxTrivia>();
            foreach (var descTrivia in astNode.DescendantTrivia())
            {

                // Example structInStruct: SingleLineCommentTrivia
                // Also:
                //  BadDirectiveTrivia -> WhitespaceTrivia, SkippedTokensTrivia
                //      SkippedTokensTrivia -> WhitespaceTrivia, SingleLineCommentTrivia, EndOfLineTrivia

                FlattenDescendentTrivia(allDescendentTrivia, descTrivia);
            }
            Console.WriteLine($"allDescendentTrivia.Count(): {allDescendentTrivia.Count()}");
            

            var triviaInLineSpan = allDescendentTrivia.Where(trivia =>
                {
                    var lineSpan = trivia.GetLocation().GetLineSpan();
                    return (
                        lineSpan.StartLinePosition.Line >= startLine
                            &&
                        lineSpan.StartLinePosition.Line <= endLine
                    );
                }
            );

            // TODO: Get trivia.Content if SingleLineDocumentationCommentTrivia

            return triviaInLineSpan.Select(trivia => trivia.Kind().ToString());

        }


        public static (int, int) GetTokenRangeByLineSpan(SyntaxNode astNode, int startLine, int endLine)
            {

            startLine--;
            endLine--;

            var allDescendentTokens = astNode.DescendantTokens().ToList();

            var startPosition = -1;
            while (startPosition == -1)
            {

                var startLineTokenList = astNode.DescendantTokens().Where(token =>
                    token.GetLocation().GetLineSpan().EndLinePosition.Line == startLine
                );

                if (startLineTokenList.Count() == 0)
                {
                    startLine--;
                    continue;
                }

                var firstDescendentToken = startLineTokenList.First();

                foreach (var token in allDescendentTokens.Select((value, i) => new { i, value }))
                {
                    if (token.value == firstDescendentToken)
                    {
                        startPosition = token.i;
                        break;
                    }
                }
            }

            var endPosition = -1;
            while (endPosition == -1)
            {

                var endLineTokenList = astNode.DescendantTokens().Where(token =>
                    token.GetLocation().GetLineSpan().StartLinePosition.Line == endLine
                );

                if (endLineTokenList.Count() == 0)
                {
                    endLine++;
                    continue;
                }

                var lastDescendentToken = endLineTokenList.Last();

                foreach (var token in allDescendentTokens.Select((value, i) => new { i, value }))
                {
                    if (token.value == lastDescendentToken)
                    {
                        endPosition = token.i;
                        break;
                    }
                }
            }

            return (startPosition, endPosition);
        }

        public static string ApplyParsedDiff(ParsedDiff parsedDiff, SourceText previousFile)
        {

            var previousFileList = previousFile.Lines.Select(x => x.ToString()).ToList();

            if (parsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<ReplaceAction>();
                foreach (var locationIndex in typedParsedDiff.SourceLocations)
                {
                    previousFileList.RemoveAt(locationIndex - 1);
                }

                var startingIndex = typedParsedDiff.SourceLocations.First() - 1;
                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    var inputText = item.value.Substring(0, item.value.LastIndexOf("\n"));
                    previousFileList.Insert(startingIndex + item.i, inputText);
                }

            }
            else if (parsedDiff.ActionType == "REMOVE")
            {
                RemoveAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<RemoveAction>();
                var indexStart = typedParsedDiff.SourceLocationStart - 1;
                var indexEnd = typedParsedDiff.SourceLocationEnd - 1;
                previousFileList.RemoveRange(indexStart, indexEnd - indexStart + 1);
            } else if (parsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<AddAction>();
                var indexStart = typedParsedDiff.PreviousSourceLocation; // No -1 since *previous* sourceLocation
                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    var inputText = item.value.Substring(0, item.value.LastIndexOf("\n"));
                    previousFileList.Insert(indexStart + item.i, inputText);
                }
            }
            return string.Join("\n", previousFileList);
        }

        public static List<String> AddTriviaToTokens(SyntaxToken[] syntaxTokens)
        {
            List<String> tokensAndTriviaInLineSpan = new List<String>();
            foreach (var token in syntaxTokens)
            {
                foreach (var leadingTrivia in token.LeadingTrivia)
                {
                    tokensAndTriviaInLineSpan.Add(leadingTrivia.Kind().ToString());
                }

                tokensAndTriviaInLineSpan.Add(token.ToString());

                // Trivia can only be leading or trailing; it is not both leading for
                // one token and trailing for another
                foreach (var trailingTrivia in token.TrailingTrivia)
                {
                    tokensAndTriviaInLineSpan.Add(trailingTrivia.Kind().ToString());
                }
            }

            return tokensAndTriviaInLineSpan;
        }

        public static void ProcessSingleRevision(PythonDataItem pythonDataItem)
        {

            const int NUM_INPUT_TOKENS = 50;

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            string pathToFile = string.Format("{0}/submodule_repos_to_analyze/{1}/{2}", solutionPath, pythonDataItem.Repo, pythonDataItem.FilePath);
            Console.WriteLine($"pathToFile: {pathToFile}");
            string previousFile;

            using (StreamReader sr = new StreamReader(pathToFile))
            {
                previousFile = sr.ReadToEnd();
            }

            var previousFileAst = CSharpSyntaxTree.ParseText(previousFile);
            var prevCodeFile = previousFileAst.GetText();

            // -------

            // Merge source side of diff with context in same list of tokens;

            var (startPosition, endPosition) = GetTokenRangeByLineSpan(
                previousFileAst.GetRoot(),
                pythonDataItem.RequiredLinesStart,
                pythonDataItem.RequiredLinesEnd
            );

            var numTokens = (endPosition - startPosition) + 1;
            if (numTokens > NUM_INPUT_TOKENS)
            {
                // Diff is too large
                Console.WriteLine($"Diff is too large; numTokens: {numTokens}");
                return;
            }
            var missingTokens = NUM_INPUT_TOKENS - numTokens;

            // TODO: Add Error tokens

            // All tokens in diff of previous file without context
            var prevCodeChunkBlockStmtTokensList = GetTokensByLineSpan(
                previousFileAst.GetRoot(),
                pythonDataItem.RequiredLinesStart,
                pythonDataItem.RequiredLinesEnd
            ).ToList();

            // Add context tokens until NUM_INPUT_TOKENS is reached
            SyntaxToken beforeToken, afterToken;
            var allDescendentTokens = previousFileAst.GetRoot().DescendantTokens().ToList();
            while (missingTokens > 0)
            {
                if (startPosition == 0 && endPosition == allDescendentTokens.Count())
                {
                    break;
                }

                // Switch between prepending and appending tokens
                if (
                    startPosition == 0 ||
                    missingTokens % 2 == 1
                ){
                    endPosition++;
                    afterToken = allDescendentTokens[endPosition];
                    prevCodeChunkBlockStmtTokensList.Add(afterToken);
                } else if (
                    endPosition == allDescendentTokens.Count() ||
                    missingTokens % 2 == 0
                ){
                    startPosition--;
                    beforeToken = allDescendentTokens[startPosition];
                    prevCodeChunkBlockStmtTokensList.Insert(0, beforeToken);
                }

                missingTokens--;
            }

            // -------
            // Get updated file data

            var updatedFile = ApplyParsedDiff(pythonDataItem.ParsedDiff, prevCodeFile);
            var updatedFileAst = CSharpSyntaxTree.ParseText(updatedFile);

            // -------

            // TODO: Use this to check for useless files (like in original file)
            var prevFileTokens = previousFileAst.GetRoot().DescendantTokens().ToList();
            var updatedFileTokens = updatedFileAst.GetRoot().DescendantTokens().ToList();
            var prevTokenIndex = new TokenIndex(prevFileTokens);
            var updatedTokenIndex = new TokenIndex(updatedFileTokens);

            // -------
            // Tokenize all target lines from diff
            
            int targetLineStart = -1;
            int targetLineEnd = -1;
            if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                targetLineStart = typedParsedDiff.SourceLocations.First();
                targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // No lines in target required
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                targetLineStart = typedParsedDiff.PreviousSourceLocation + 1;
                targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
            }

            IEnumerable<SyntaxToken> updatedCodeChunkBlockStmtTokensIEnum = Enumerable.Empty<SyntaxToken>();

            // No output with "REMOVE"
            if ((pythonDataItem.ParsedDiff.ActionType == "REPLACE") || (pythonDataItem.ParsedDiff.ActionType == "ADD"))
            {

                if ((targetLineStart == -1) || (targetLineEnd == -1))
                {
                    Console.WriteLine($"Error parsing target");
                    Console.WriteLine($"targetLineStart: {targetLineStart}");
                    Console.WriteLine($"targetLineEnd: { targetLineEnd}");
                    System.Environment.Exit(1);
                }

                // var changeSpan = new TextSpan(targetLineStart, targetLineEnd - targetLineStart);
                updatedCodeChunkBlockStmtTokensIEnum = GetTokensByLineSpan(
                    updatedFileAst.GetRoot(),
                    targetLineStart,
                    targetLineEnd
                );

            }

            var updatedCodeChunkBlockStmtTokens = updatedCodeChunkBlockStmtTokensIEnum.ToArray();

            // -------
            // Zero-index all variable names

            var prevCodeChunkBlockStmtTokens = prevCodeChunkBlockStmtTokensList.ToArray();
            var allTokens = new SyntaxToken[updatedCodeChunkBlockStmtTokens.Length + prevCodeChunkBlockStmtTokens.Length];
            updatedCodeChunkBlockStmtTokens.CopyTo(allTokens, 0);
            prevCodeChunkBlockStmtTokens.CopyTo(allTokens, updatedCodeChunkBlockStmtTokens.Length);

            // Creating map of {someVarName: VAR0}
            var zeroIndexedVariableNameMap = new Dictionary<string, string>();
            (zeroIndexedVariableNameMap, allTokens) = ApplyAndUpdateIndexVariableNames(zeroIndexedVariableNameMap, allTokens);
            (zeroIndexedVariableNameMap, prevCodeChunkBlockStmtTokens) = ApplyAndUpdateIndexVariableNames(zeroIndexedVariableNameMap, prevCodeChunkBlockStmtTokens);
            (zeroIndexedVariableNameMap, updatedCodeChunkBlockStmtTokens) = ApplyAndUpdateIndexVariableNames(zeroIndexedVariableNameMap, updatedCodeChunkBlockStmtTokens);

            // -------
            // Generate finished list of tokens in the change including formatting
            // Does not work though if only trivia in span (no tokens); See next section for fix.

            var prevCodeChunkBlockStmtTextTokens = AddTriviaToTokens(prevCodeChunkBlockStmtTokens).ToArray();
            var updatedCodeChunkBlockStmtTextTokens = AddTriviaToTokens(updatedCodeChunkBlockStmtTokens).ToArray();

            // -------
            // In case that all added lines for ADD/REPLACE are trivia; In this case,
            // there is no token to get Leading/Trailing Trivia from

            if ((pythonDataItem.ParsedDiff.ActionType == "REPLACE") || (pythonDataItem.ParsedDiff.ActionType == "ADD"))
            {
                if (updatedCodeChunkBlockStmtTextTokens.Count() == 0)
                {
                    updatedCodeChunkBlockStmtTextTokens = GetTriviaByLineSpan(
                        updatedFileAst.GetRoot(),
                        targetLineStart,
                        targetLineEnd
                    ).ToArray();
                }
            }

            // -------
            // Tokenize DiagnosticMessage

            foreach (var diag in pythonDataItem.DiagnosticOccurances)
            {
                diag.TokenizedMessage = new List<string>();
                foreach (var wordToken in diag.Message.Split(" "))
                {
                    // DiagnosticMessage contains variable name
                    if (wordToken.StartsWith("'") && wordToken.EndsWith("'"))
                    {
                        var wordTokenCore = wordToken.Remove(0,1);
                        wordTokenCore = wordTokenCore.Remove(wordTokenCore.Length - 1,1);

                        // Could also be that variable name is outside of scope - not worth
                        // indexing those, otherwise we have VAR-1000, etc.
                        if (zeroIndexedVariableNameMap.ContainsKey(wordTokenCore))
                        {
                            var wordTokenIndexed = zeroIndexedVariableNameMap[wordTokenCore];
                            diag.TokenizedMessage.Add(wordTokenIndexed);
                        } else
                        {
                            // Can be difficult to find in map (e.g. 'this[]')
                            Console.WriteLine($"Weird token! : {wordTokenCore}");
                            diag.TokenizedMessage.Add($"UNKNOWN: {wordTokenCore}");
                        }
                    }
                    else
                    {
                        foreach ( var splitWordToken in Regex.Split(wordToken, @"(?=[.!?\\-])|(?<=[.!?\\-])").ToList())
                        {
                            if (splitWordToken != "")
                                diag.TokenizedMessage.Add(splitWordToken.ToLower());
                        }
                    }
                }
            }

            // -------
            // Write all calculated data to JSONObject

            if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
                pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // Nothing to tokenize
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
                pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }

            pythonDataItem.TokenizedFileContext = prevCodeChunkBlockStmtTextTokens.ToList();

            return;
        }

        private static (Dictionary<string, string>, SyntaxToken[]) ApplyAndUpdateIndexVariableNames(Dictionary<string, string> varNameMap, IEnumerable<SyntaxToken> syntaxTokenArray)
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
                if (varNameMap.ContainsKey(tokenName))
                {
                    // Already have this saved in dict
                    newTokenName = varNameMap[tokenName];
                }
                else
                {
                    newTokenName = "VAR" + varNameMap.Count;
                    varNameMap[tokenName] = newTokenName;

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

            return (varNameMap, newSyntaxTokenArray.ToArray());
        }

        public static void DumpRevisionDataForNeuralTraining(string pythonDataDir, string newDataDir)
        {

            string[] refinedJSONpaths = Directory.GetFiles(pythonDataDir, "*.json",
                                         SearchOption.TopDirectoryOnly);

            Console.WriteLine($"refinedJSONpaths.Count(): {refinedJSONpaths.Count()}");
            Console.WriteLine($"refinedJSONpaths.First(): {refinedJSONpaths.First()}");

            foreach (var JSONpath in refinedJSONpaths)
            {
                try
                {

                    using (StreamReader sr = new StreamReader(JSONpath))
                    {

                        Console.WriteLine($"JSONpath: {JSONpath}");

                        string json = sr.ReadToEnd();
                        PythonDataItem pythonDataItem = JsonConvert.DeserializeObject<PythonDataItem>(json);

                        if (pythonDataItem.TokenizedFileContext != null)
                        {
                            // File has already been tokenized
                            continue;
                        }

                        try
                        {
                            ProcessSingleRevision(pythonDataItem);
                        }
                        catch (Exception e)
                        {
                            Console.WriteLine($"e: {e}");
                            System.Environment.Exit(1);
                        }

                        pythonDataItem.RemoveOldData();
                        var newDataItem = JsonConvert.SerializeObject(
                            pythonDataItem,
                            Formatting.Indented,
                            new JsonSerializerSettings
                            {
                                NullValueHandling = NullValueHandling.Ignore
                            }
                        );

                        var newFilename = Path.GetFileName(JSONpath);
                        var newFilepath = Path.Combine(newDataDir, newFilename);
                        System.IO.File.WriteAllText(newFilepath, newDataItem);

                    }
                }
                catch (Exception e) {
                    Console.WriteLine($"e: {e}");
                }
            }

        }

        private static readonly HashSet<string> keywords =
            new HashSet<string>() {"VAR0", "int", "long", "string", "float", "LITERAL", "var"};

        private static bool IsValidCodeChunkTokens(IEnumerable<string> tokens)
        {
            var validTokenCount = tokens.Count(token => !keywords.Contains(token) && !token.All(char.IsPunctuation));

            return validTokenCount > 0;
        }
    }

    public class TokenIndex
    {
        private IList<SyntaxToken> tokens;
        public Dictionary<TextSpan, (SyntaxToken SyntaxToken, int Position)> SpanToTokenIndex;

        public TokenIndex(IEnumerable<SyntaxToken> tokens)
        {
            this.tokens = new List<SyntaxToken>(tokens);
        }

        public IEnumerable<SyntaxToken> GetTokensInSpan(TextSpan querySpan)
        {
            var querySpanStart = querySpan.Start;
            var querySpanEnd = querySpan.End;

            return GetTokensInSpan(querySpanStart, querySpanEnd);
        }

        public TokenIndex WithVariableNameMap(IDictionary<string, string> variableNameMap)
        {
            var retainedTokens = tokens.Where(token => variableNameMap.ContainsKey(token.ValueText))
                .Select(token => SyntaxFactory.Token(token.LeadingTrivia, token.Kind(), token.Text, variableNameMap[token.ValueText], token.TrailingTrivia));

            return new TokenIndex(retainedTokens);
        }

        public TokenIndex InitInvertedIndex()
        {
            this.SpanToTokenIndex = new Dictionary<TextSpan, (SyntaxToken SyntaxToken, int Position)>();

            for (int i = 0; i < this.tokens.Count; i++)
            {
                var curToken = this.tokens[i];
                var key = curToken.Span;
                SpanToTokenIndex[key] = (curToken, i);
            }

            return this;
        }

        public IEnumerable<SyntaxToken> GetTokensInSpan(int start, int end)
        {
            var queryTokens = tokens.Where(token => token.SpanStart >= start).TakeWhile(token => token.Span.End <= end);

            return queryTokens;
        }

        public (SyntaxToken? SyntaxToken, int Position) GetTokenAndPositionBySpan(TextSpan span)
        {
            if (this.SpanToTokenIndex.ContainsKey(span))
            {
                return this.SpanToTokenIndex[span];
            }

            return (null, -1);
        }
    }
}
