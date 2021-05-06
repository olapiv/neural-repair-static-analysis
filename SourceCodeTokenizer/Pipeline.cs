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

        public static IEnumerable<SyntaxToken> GetTokensByLineSpan(SyntaxNode astNode, SourceText sourceText, int startLine, int endLine)
        {

            startLine--;
            endLine--;

            var tokensInLineSpan = astNode.DescendantTokens().Where(token =>
                token.GetLocation().GetLineSpan().EndLinePosition.Line == startLine
                ||
                token.GetLocation().GetLineSpan().StartLinePosition.Line == endLine
            );

            return tokensInLineSpan;
        }

        public static (int, int) GetTokenRangeByLineSpan(SyntaxNode astNode, SourceText sourceText, int startLine, int endLine)
        {

            startLine--;
            endLine--;
            Console.WriteLine($"startLine: {startLine}");
            Console.WriteLine($"endLine: {endLine}");

            var firstDescendentToken = astNode.DescendantTokens().Where(token =>
                token.GetLocation().GetLineSpan().EndLinePosition.Line == startLine
            ).First();
            Console.WriteLine($"firstDescendentToken.ValueText: {firstDescendentToken.ValueText}");

            var lastDescendentToken = astNode.DescendantTokens().Where(token =>
                token.GetLocation().GetLineSpan().StartLinePosition.Line == endLine
            ).Last();
            Console.WriteLine($"lastDescendentTokens.ValueText: {lastDescendentToken.ValueText}");

            var allDescendentTokens = astNode.DescendantTokens().ToList();

            var startPosition = -1;
            var endPosition = -1;
            foreach (var token in allDescendentTokens.Select((value, i) => new { i, value }))
            {
                if (token.value == firstDescendentToken)
                {
                    Console.WriteLine($"Found firstDescendentToken! token.value: {token.value}");
                    startPosition = token.i;
                } else if (token.value == lastDescendentToken)
                {
                    Console.WriteLine($"Found lastDescendentTokens! token.value: {token.value}");
                    endPosition = token.i;
                }
            }
            return (startPosition, endPosition);
        }

        public static IEnumerable<ChangeSample> GetChangesBetweenAsts(SyntaxTree previousFileAst, SyntaxTree updatedFileAst)
        {
            var changesWithContext = DiffInfo.GetChangesWithContext(previousFileAst, updatedFileAst);
            return changesWithContext;
        }

        public static string ApplyParsedDiff(ParsedDiff parsedDiff, String previousFile)
        {
            List<string> previousFileList = Regex.Split(previousFile, @"(?<=[\\r\\n])").ToList();
            Console.WriteLine($"previousFileList.First(): {previousFileList.First()}");

            if (parsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<ReplaceAction>();
                foreach (var locationIndex in typedParsedDiff.SourceLocations)
                {
                    previousFileList.RemoveAt(locationIndex);
                }

                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    previousFileList.Insert(typedParsedDiff.SourceLocations.First() + item.i, item.value);
                }

            }
            else if (parsedDiff.ActionType == "REMOVE")
            {
                RemoveAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<RemoveAction>();
                previousFileList.RemoveRange(typedParsedDiff.SourceLocationStart, typedParsedDiff.SourceLocationEnd - typedParsedDiff.SourceLocationStart + 1);
            } else if (parsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)parsedDiff.Action).ToObject<AddAction>();
                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    previousFileList.Insert(typedParsedDiff.PreviousSourceLocation + item.i, item.value);
                }
            }
            Console.WriteLine($"previousFileList: {previousFileList.Count()}");
            return string.Join("", previousFileList);
        }

        public static void ProcessSingleRevision(PythonDataItem pythonDataItem)
        {

            const int NUM_INPUT_TOKENS = 50;

            string solutionPath = Directory.GetParent(System.IO.Directory.GetCurrentDirectory()).Parent.Parent.Parent.FullName;
            // string pathToFile = @"{solutionPath}/{pythonDataItem.Repo}/{pythonDataItem.FilePath}";
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
                prevCodeFile,
                pythonDataItem.RequiredLinesStart,
                pythonDataItem.RequiredLinesEnd
            );
            Console.WriteLine($"startPosition: {startPosition}");
            Console.WriteLine($"endPosition: {endPosition}");

            var numTokens = endPosition - startPosition;
            if (numTokens > NUM_INPUT_TOKENS)
            {
                // Diff is too large
                Console.WriteLine($"Diff is too large; numTokens: {numTokens}");
                return;
            }
            var missingTokens = NUM_INPUT_TOKENS - numTokens;
            Console.WriteLine($"missingTokens: {missingTokens}");

            // TODO: Add Error tokens

            // TODO: Avoid getting entire parent node here

            // All tokens in diff of previous file without context
            var prevCodeChunkBlockStmtTokensList = GetTokensByLineSpan(
                previousFileAst.GetRoot(),
                prevCodeFile,
                pythonDataItem.RequiredLinesStart,
                pythonDataItem.RequiredLinesEnd
            );
            Console.WriteLine($"prevCodeChunkBlockStmtTokensList.Count(): {prevCodeChunkBlockStmtTokensList.Count()}");

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
                    prevCodeChunkBlockStmtTokensList.Append(afterToken);
                } else if (
                    endPosition == allDescendentTokens.Count() ||
                    missingTokens % 2 == 0
                ){
                    startPosition--;
                    beforeToken = allDescendentTokens[startPosition];
                    prevCodeChunkBlockStmtTokensList.Prepend(beforeToken);
                }

                missingTokens--;
            }

            Console.WriteLine($"allDescendentTokens.Count(): {allDescendentTokens.Count()}");

            // -------
            // Get updated file data

            var updatedFile = ApplyParsedDiff(pythonDataItem.ParsedDiff, previousFile);
            var updatedFileAst = CSharpSyntaxTree.ParseText(updatedFile);
            var updatedCodeFile = updatedFileAst.GetText();

            Console.WriteLine($"updatedCodeFile.Count(): {updatedCodeFile.Lines.Count()}");

            // -------

            var prevFileTokens = previousFileAst.GetRoot().DescendantTokens().ToList();
            var updatedFileTokens = updatedFileAst.GetRoot().DescendantTokens().ToList();
            
            // -------

            // TODO: Use this to check for useless files (like in original file)
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
                targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count();
            }

            IEnumerable<SyntaxToken> updatedCodeChunkBlockStmtTokensIEnum = Enumerable.Empty<SyntaxToken>();
            Console.WriteLine($"targetLineStart: {targetLineStart}");
            Console.WriteLine($"targetLineEnd: {targetLineEnd}");
            if (targetLineStart != -1)  // Otherwise no need to tokenize output at all
            {
                var updatedTreeText = updatedFileAst.GetText();
                // var changeSpan = new TextSpan(targetLineStart, targetLineEnd - targetLineStart);

                updatedCodeChunkBlockStmtTokensIEnum = GetTokensByLineSpan(
                    updatedFileAst.GetRoot(),
                    updatedCodeFile,
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

            // Creating map of {VAR0: someVarName}
            IDictionary<string, string> zeroIndexedVariableNameMap;
            IEnumerable<SyntaxToken> allZeroIndexedTokens = Enumerable.Empty<SyntaxToken>();
            (allZeroIndexedTokens, zeroIndexedVariableNameMap) =
                zeroIndexVariableNames(allTokens);

            prevCodeChunkBlockStmtTokens = zeroIndexVariableNames(prevCodeChunkBlockStmtTokens, zeroIndexedVariableNameMap);
            prevCodeChunkBlockStmtTokens = zeroIndexVariableNames(prevCodeChunkBlockStmtTokens, zeroIndexedVariableNameMap);

            // -------
            // Generate finished list of tokens in the change (without formatting)

            var prevCodeChunkBlockStmtTextTokens =
                prevCodeChunkBlockStmtTokens.Select(token => token.ValueText).ToArray();
            var updatedCodeChunkBlockStmtTextTokens =
                updatedCodeChunkBlockStmtTokens.Select(token => token.ValueText).ToArray();

            // -------
            // Tokenize DiagnosticMessage

            var prevFileTextTokens = prevFileTokens.Select(token => token.ValueText).ToArray();
            foreach (var diag in pythonDataItem.DiagnosticOccurances)
            {
                diag.TokenizedMessage = new List<string>();
                foreach (var wordToken in diag.Message.Split(" "))
                {
                    // DiagnosticMessage contains variable name
                    if (wordToken.StartsWith("'") && wordToken.EndsWith("'"))
                    {
                        wordToken.Remove(0).Remove(wordToken.Length - 1);
                        // Could also be that variable name is outside of scope - not worth
                        // indexing those, otherwise we have VAR-1000, etc.
                        if (zeroIndexedVariableNameMap.ContainsKey(wordToken))
                        {
                            var wordTokenIndexed = zeroIndexedVariableNameMap[wordToken];
                            diag.TokenizedMessage.Append(wordToken);
                        }
                    }
                    else
                    {
                        diag.TokenizedMessage.Append(wordToken);
                    }
                }
            }

            // -------
            // Write all calculated data to JSONObject

            if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<ReplaceAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // Nothing to tokenize
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = ((JObject)pythonDataItem.ParsedDiff.Action).ToObject<AddAction>();
                typedParsedDiff.TokenizedTargetLines = updatedCodeChunkBlockStmtTextTokens;
            }

            // TODO: Check that all formatting is tokenized as well
            pythonDataItem.TokenizedFileContext = prevCodeChunkBlockStmtTextTokens.ToList();

            return;
        }

        private static string changeEntryDatumToJsonString(dynamic entry, bool withCommitMessage=false)
        {
            var jsonObj = new JObject();
            jsonObj["Id"] = entry.Id;
            jsonObj["PrevCodeChunk"] = entry.PrevCodeChunk;
            jsonObj["UpdatedCodeChunk"] = entry.UpdatedCodeChunk;

            jsonObj["PrevCodeChunkTokens"] = new JArray(entry.PrevCodeChunkTokens);
            jsonObj["UpdatedCodeChunkTokens"] = new JArray(entry.UpdatedCodeChunkTokens);

            jsonObj["PrevCodeAST"] = entry.PrevCodeAST;
            jsonObj["UpdatedCodeAST"] = entry.UpdatedCodeAST;

            jsonObj["PrecedingContext"] = new JArray(entry.PrecedingContext);
            jsonObj["SucceedingContext"] = new JArray(entry.SucceedingContext);

            if (withCommitMessage)
                jsonObj["CommitMessage"] = entry.CommitMessage;

            var json = JsonConvert.SerializeObject(jsonObj, Formatting.None);

            return json;
        }

        private static SyntaxToken[] zeroIndexVariableNames(
            IEnumerable<SyntaxToken> tokens, IDictionary<string, string> varNameMap)
        {
            SyntaxToken generateNewTokenName(SyntaxToken token)
            {
                if (token.IsKind(SyntaxKind.IdentifierToken))
                {
                    var tokenName = token.ValueText;
                    if (tokenName.StartsWith("VAR"))
                    {
                        string newTokenName;
                        if (varNameMap.ContainsKey(tokenName))
                            newTokenName = varNameMap[tokenName];
                        else
                        {
                            newTokenName = "VAR" + varNameMap.Count;
                            varNameMap[tokenName] = newTokenName;
                        }

                        return SyntaxFactory.Identifier(newTokenName);
                    }
                }

                return token;
            }

            var renamedTokens = tokens.Select(generateNewTokenName).ToArray();

            return renamedTokens;
        }

        private static (BlockSyntax, BlockSyntax, IDictionary<string, string>) zeroIndexVariableNames(SyntaxNode prevCodeNode, SyntaxNode updatedCodeNode)
        {
            var varNameMap = new Dictionary<string, string>();

            SyntaxToken generateNewTokenName(SyntaxToken token)
            {
                if (token.IsKind(SyntaxKind.IdentifierToken))
                {
                    var tokenName = token.ValueText;
                    if (tokenName.StartsWith("VAR"))
                    {
                        string newTokenName;
                        if (varNameMap.ContainsKey(tokenName))
                            newTokenName = varNameMap[tokenName];
                        else
                        {
                            newTokenName = "VAR" + varNameMap.Count;
                            varNameMap[tokenName] = newTokenName;
                        }

                        return SyntaxFactory.Identifier(newTokenName);
                    }
                }
                
                return token;
            }

            var newPrevCodeNode = prevCodeNode.ReplaceTokens(prevCodeNode.DescendantTokens(), (token, _) => generateNewTokenName(token));
            var newUpdatedCodeNode = updatedCodeNode.ReplaceTokens(updatedCodeNode.DescendantTokens(), (token, _) => generateNewTokenName(token));

            return ((BlockSyntax)newPrevCodeNode, (BlockSyntax)newUpdatedCodeNode, varNameMap);
        }

        private static (IEnumerable<SyntaxToken>, IDictionary<string, string>) zeroIndexVariableNames(IEnumerable<SyntaxToken> syntaxTokenArray)
        {
            var varNameMap = new Dictionary<string, string>();

            SyntaxToken generateNewTokenName(SyntaxToken token)
            {
                if (token.IsKind(SyntaxKind.IdentifierToken))
                {
                    var tokenName = token.ValueText;
                    if (tokenName.StartsWith("VAR"))
                    {
                        string newTokenName;
                        if (varNameMap.ContainsKey(tokenName))
                            newTokenName = varNameMap[tokenName];
                        else
                        {
                            newTokenName = "VAR" + varNameMap.Count;
                            varNameMap[tokenName] = newTokenName;
                        }

                        return SyntaxFactory.Identifier(newTokenName);
                    }
                }

                return token;
            }

            IEnumerable<SyntaxToken> newSyntaxTokenArray = Enumerable.Empty<SyntaxToken>();
            foreach (var syntaxToken in syntaxTokenArray)
            {
                newSyntaxTokenArray.Append(generateNewTokenName(syntaxToken));
            }

            return (newSyntaxTokenArray, varNameMap);
        }

        public static void DumpRevisionDataForNeuralTraining(string pythonDataDir, string grammarPath)
        {

            // var syntaxHelper = new JsonSyntaxTreeHelper(grammarPath);

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
                        }

                        // TODO: Write pythonDataItem to file again
                        var newDataItem = JsonConvert.SerializeObject(pythonDataItem, Formatting.Indented);
                        Console.WriteLine($"newDataItem: {newDataItem}");

                        System.Environment.Exit(1);
                        break;

                    }
                }
                catch (Exception e) {
                    Console.WriteLine($"e: {e}");
                }
            }

        }

        public static IEnumerable<string> ReadRevisionData(string revisionDataFilePath)
        {
            using (var sr = new StreamReader(revisionDataFilePath))
            {
                while (!sr.EndOfStream)
                {
                    var line = sr.ReadLine();

                    yield return line;
                }
            }
        }

        // Not using this as it for instance also skips EnumDeclaration
        static readonly HashSet<SyntaxKind> allowedSyntaxKinds = new HashSet<SyntaxKind>()
        {
            SyntaxKind.LocalDeclarationStatement,
            SyntaxKind.ExpressionStatement
        };

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
