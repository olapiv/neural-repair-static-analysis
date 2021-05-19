﻿using System;
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

            // Example structInStruct: SingleLineCommentTrivia
            // Example 2:
            //  BadDirectiveTrivia -> WhitespaceTrivia, SkippedTokensTrivia
            //      SkippedTokensTrivia -> WhitespaceTrivia, SingleLineCommentTrivia, EndOfLineTrivia
            // Example 3:
            // SingleLineDocumentationCommentTrivia --> 3x DocumentationCommentExteriorTrivia

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

            var allDescendentTrivia = new List<SyntaxTrivia>();
            foreach (var descTrivia in astNode.DescendantTrivia())
            {
                FlattenDescendentTrivia(allDescendentTrivia, descTrivia);
            }
            
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

            // ---------            

            // For debugging purposes:
            var numLines = triviaInLineSpan.Where(trivia =>
                trivia.Kind().ToString() == "EndOfLineTrivia"
            ).Count();

            if (numLines != (endLine - startLine + 1))
            {

                Console.WriteLine($"numLines not equal to line difference!");

                foreach (var trivia in triviaInLineSpan)
                {
                    Console.WriteLine($"-----");
                    Console.WriteLine($"trivia.Kind(): {trivia.Kind()}");
                    Console.WriteLine($"trivia.StartLinePosition.Line: {trivia.GetLocation().GetLineSpan().StartLinePosition.Line}");
                    Console.WriteLine($"trivia.EndLinePosition.Line: {trivia.GetLocation().GetLineSpan().EndLinePosition.Line}");

                    if (trivia.Kind().ToString() == "SingleLineDocumentationCommentTrivia")
                    {
                        Console.WriteLine($"trivia.GetHashCode(): {trivia.GetHashCode()}");
                        Console.WriteLine($"trivia.ToFullString(): {trivia.ToFullString()}");
                        Console.WriteLine($"trivia.GetType(): {trivia.GetType()}");
                        Console.WriteLine($"trivia.RawKind: {trivia.RawKind}");
                    }
                }

            }
            Console.WriteLine($"----------");

            // ---------

            // TODO: Get trivia.Content if SingleLineDocumentationCommentTrivia
            // Problem here - have to manually deal with line breaks, etc again

            //var expandedTrivia = new List<String>();
            //foreach(var trivia in triviaInLineSpan)
            //{
            //    if (trivia.Kind().ToString() == "SingleLineDocumentationCommentTrivia")
            //    {
                    
            //        foreach (var splitWordToken in trivia.ToFullString().Split(" "))
            //        {
            //            if (splitWordToken != "")
            //                expandedTrivia.Add(splitWordToken.ToLower());
            //        }

            //    } else
            //    {
            //        expandedTrivia.Add(trivia.Kind().ToString());
            //    }
            //}
            //return expandedTrivia;

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

                // TODO: Delete this; for debugging
                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    Console.WriteLine($"previousFileList[{startingIndex + item.i}]: {previousFileList[startingIndex + item.i]}");
                }
                var nextLineIndex = startingIndex + typedParsedDiff.TargetLines.Count();
                Console.WriteLine($"previousFileList[{nextLineIndex}]: {previousFileList[nextLineIndex]}");

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

                // TODO: Delete this; for debugging
                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    Console.WriteLine($"previousFileList[{indexStart + item.i}]: {previousFileList[indexStart + item.i]}");
                }
                var nextLineIndex = indexStart + typedParsedDiff.TargetLines.Count();
                Console.WriteLine($"previousFileList[{nextLineIndex}]: {previousFileList[nextLineIndex]}");

            }
            return string.Join("\n", previousFileList);
        }

        public static (String[], int) AddTriviaToTokens(SyntaxToken[] syntaxTokens)
        {
            var firstLine = 1000000000;
            int triviaOrTokenLine;
            List<String> tokensAndTriviaInLineSpan = new List<String>();
            foreach (var token in syntaxTokens)
            {
                foreach (var leadingTrivia in token.LeadingTrivia)
                    tokensAndTriviaInLineSpan.Add(leadingTrivia.Kind().ToString());

                tokensAndTriviaInLineSpan.Add(token.ToString());

                // This is a problem if variable has been zero-indexed (position is 0)
                triviaOrTokenLine = token.GetLocation().GetLineSpan().StartLinePosition.Line;
                if ((triviaOrTokenLine != 0) && (triviaOrTokenLine < firstLine))
                    firstLine = triviaOrTokenLine;
                

                // Trivia can only be leading or trailing; it is not both leading for
                // one token and trailing for another
                foreach (var trailingTrivia in token.TrailingTrivia)
                {
                    tokensAndTriviaInLineSpan.Add(trailingTrivia.Kind().ToString());
                }
            }

            return (tokensAndTriviaInLineSpan.ToArray(), firstLine);
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
            IEnumerable<SyntaxToken> updatedCodeChunkBlockStmtTokensIEnum = Enumerable.Empty<SyntaxToken>();

            // No output with "REMOVE"
            if (pythonDataItem.ParsedDiff.ActionType != "REMOVE")
            {
                if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
                {
                    ReplaceAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                    targetLineStart = typedParsedDiff.SourceLocations.First();
                    targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
                } 
                else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
                {
                    AddAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                    targetLineStart = typedParsedDiff.PreviousSourceLocation + 1;
                    targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count() - 1;
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

            // TODO: Get firstLinePrev & firstLineNew here already

            // firstLinePrev/firstLineNew are offsets for other indices
            var (prevCodeChunkBlockStmtTextTokens, firstLinePrev) = AddTriviaToTokens(prevCodeChunkBlockStmtTokens);
            var (updatedCodeChunkBlockStmtTextTokens, firstLineNew) = AddTriviaToTokens(updatedCodeChunkBlockStmtTokens);

            Console.WriteLine($"firstLinePrev : {firstLinePrev}");
            Console.WriteLine($"firstLineNew : {firstLineNew}");

            // -------
            // In case that all added lines for ADD/REPLACE are trivia; In this case,
            // there is no token to get Leading/Trailing Trivia from

            if ((pythonDataItem.ParsedDiff.ActionType == "REPLACE") || (pythonDataItem.ParsedDiff.ActionType == "ADD"))
            {
                if (updatedCodeChunkBlockStmtTextTokens.Count() == 0)
                {
                    Console.WriteLine($"Empty updatedCodeChunkBlockStmtTextTokens! Adding trivia without tokens then.");

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
                typedParsedDiff.SourceLocations = typedParsedDiff.SourceLocations.Select(x => x - firstLinePrev).ToList().ToArray();
                pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // Nothing to tokenize, only change offsets
                RemoveAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<RemoveAction>();
                typedParsedDiff.SourceLocationStart = typedParsedDiff.SourceLocationStart - firstLinePrev;
                typedParsedDiff.SourceLocationEnd = typedParsedDiff.SourceLocationStart - firstLinePrev;
                pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
                Console.WriteLine($"firstLinePrev: {firstLinePrev}");
                Console.WriteLine($"typedParsedDiff.PreviousSourceLocation Before: {typedParsedDiff.PreviousSourceLocation}");
                typedParsedDiff.PreviousSourceLocation -= firstLinePrev;
                Console.WriteLine($"typedParsedDiff.PreviousSourceLocation After: {typedParsedDiff.PreviousSourceLocation}");
                pythonDataItem.ParsedDiff.Action = typedParsedDiff;
            }

            pythonDataItem.TokenizedFileContext = prevCodeChunkBlockStmtTextTokens.ToList();
            pythonDataItem.DiagnosticOccurances.Select(x => x.Line - firstLinePrev);

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

}
