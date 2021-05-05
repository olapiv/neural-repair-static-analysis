using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Dynamic;
using System.IO;
using System.Text;
using System.Linq;
using System.Runtime.InteropServices;
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

        public static IEnumerable<SyntaxNode> GetNodesByLineSpan(SyntaxNode astNode, SourceText sourceText, int startLine, int endLine)
        {

            for (var lineId = startLine;
                lineId <= endLine;
                lineId++)
            {
                var lineSource = sourceText.Lines[lineId];

                // Keep formatting
                //if (string.IsNullOrWhiteSpace(lineSource.ToString()))
                //    continue;

                var lineSpan = lineSource.Span;

                // Keep formatting
                //if (lineSpan.IsEmpty)
                //    continue;

                var node = astNode.FindNode(lineSpan);

                yield return node;
            }
        }

        public static Tuple<int, int> GetTokenRangeByLineSpan(SyntaxNode astNode, SourceText sourceText, int startLine, int endLine)
        {

            var descendentTokens = astNode.DescendantTokens().ToList();

            var lineSourceStart = sourceText.Lines[startLine];
            var lineSpanStart = lineSourceStart.Span;
            var nodeStart = astNode.FindNode(lineSpanStart);
            var firstDescendentToken = nodeStart.DescendantTokens().ToList().First();

            var lineSourceEnd = sourceText.Lines[endLine];
            var lineSpanEnd = lineSourceStart.Span;
            var nodeEnd = astNode.FindNode(lineSpanStart);
            var lastDescendentTokens = nodeStart.DescendantTokens().ToList().Last();

            var startPosition = -1;
            var endPosition = -1;
            foreach (var token in descendentTokens.Select((value, i) => new { i, value }))
            {
                if (token.value == firstDescendentToken)
                {
                    startPosition = token.i;
                } else if (token.value == lastDescendentTokens)
                {
                    endPosition = token.i;
                }
            }
            return Tuple.Create(startPosition, endPosition);
        }

        public static IEnumerable<ChangeSample> GetChangesBetweenAsts(SyntaxTree previousFileAst, SyntaxTree updatedFileAst)
        {
            var changesWithContext = DiffInfo.GetChangesWithContext(previousFileAst, updatedFileAst);
            return changesWithContext;
        }

        public static string ApplyParsedDiff(ParsedDiff parsedDiff, String previousFile)
        {
            List <string> previousFileList = previousFile.Split("\n").ToList();
            if (parsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = parsedDiff.Action;
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
                RemoveAction typedParsedDiff = parsedDiff.Action;
                previousFileList.RemoveRange(typedParsedDiff.SourceLocationStart, typedParsedDiff.SourceLocationEnd - typedParsedDiff.SourceLocationStart + 1);
            } else if (parsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = parsedDiff.Action;

                foreach (var item in typedParsedDiff.TargetLines.Select((value, i) => new { i, value }))
                {
                    previousFileList.Insert(typedParsedDiff.PreviousSourceLocation + item.i, item.value);
                }
            }
            return string.Join("", previousFileList);
        }

        public static SyntaxToken[] GetTokens(SyntaxNode fileAST, SourceText codeFile, int startLine, int endLine)
        {
            // Only consider SyntaxKind in allowedSytaxKinds
            var codeChunkNodes = GetNodesByLineSpan(
                fileAST,
                codeFile,
                startLine,
                endLine
            );
            if (codeChunkNodes.Any(node => !allowedSytaxKinds.Contains(node.Kind())))
                return null;

            // Create SyntaxBlock out of list of SyntaxNode (probably starts/ends with "{","}")
            // Does "StatementSyntax" remove spaces, etc.? 
            var codeChunkBlockStmt = SyntaxFactory.Block(codeChunkNodes.Select(node => (StatementSyntax)node));

            // .Skip(1).SkipLast(1) probably to remove "{","}"
            var codeChunkBlockStmtTokens = codeChunkBlockStmt.DescendantTokens().Skip(1).SkipLast(1).ToArray();
            return codeChunkBlockStmtTokens;
        }

        public static void ProcessSingleRevision(PythonDataItem pythonDataItem, JsonSyntaxTreeHelper jsonSyntaxTreeHelper)
        {

            const int NUM_INPUT_TOKENS = 50;

            // TODO: Get previous file from repo
            var pathToFile = @"{pythonDataItem.Repo}/{pythonDataItem.FilePath}";
            string previousFile;

            using (StreamReader sr = new StreamReader(pathToFile))
            {
                previousFile = sr.ReadToEnd();
            }

            var previousFileAst = CSharpSyntaxTree.ParseText(previousFile);

            // Probably take this out
            (SyntaxNode canonicalPrevFileAst, Dictionary<string, string> prevFileVariableNameMap) = Canonicalization.CanonicalizeSyntaxNode(previousFileAst.GetRoot(), extractAllVariablesFirst:true);

            var prevCodeFile = canonicalPrevFileAst.GetText();

            // -------

            // Merge context and change in same list of tokens;

            var positions = GetTokenRangeByLineSpan(
                canonicalPrevFileAst,
                prevCodeFile,
                pythonDataItem.requiredLinesStart,
                pythonDataItem.requiredLinesEnd
            );
            var startPosition = positions.Item1;
            var endPosition = positions.Item2;

            var numTokens = endPosition - startPosition;
            if (numTokens > NUM_INPUT_TOKENS)
            {
                // Diff is too large
                yield return null;
            }
            var missingTokens = NUM_INPUT_TOKENS - numTokens;

            // All tokens in diff of previous file without context
            var prevCodeChunkBlockStmtTokensList = GetTokens(
                canonicalPrevFileAst,
                prevCodeFile,
                pythonDataItem.requiredLinesStart,
                pythonDataItem.requiredLinesEnd
            ).ToList();

            // Add context tokens until NUM_INPUT_TOKENS is reached
            SyntaxToken beforeToken, afterToken;
            var allDescendentTokens = canonicalPrevFileAst.DescendantTokens().ToList();
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

            // -------
            // Get updated file data

            var updatedFile = ApplyParsedDiff(pythonDataItem.ParsedDiff, previousFile);
            var updatedFileAst = CSharpSyntaxTree.ParseText(updatedFile);

            // TODO: Think about removing this
            (SyntaxNode canonicalUpdatedFileAst, Dictionary<string, string> updatedFileVariableNameMap) = Canonicalization.CanonicalizeSyntaxNode(updatedFileAst.GetRoot(), prevFileVariableNameMap);
            var updatedCodeFile = canonicalUpdatedFileAst.GetText();

            // -------

            // TODO: Use these to parse DiagnosticMessage
            var prevFileTokens = canonicalPrevFileAst.DescendantTokens().ToList();
            var updatedFileTokens = canonicalUpdatedFileAst.DescendantTokens().ToList();

            // Can be used to check for useless files
            var prevTokenIndex = new TokenIndex(prevFileTokens);
            var updatedTokenIndex = new TokenIndex(updatedFileTokens);

            // -------
            // Tokenize all target lines from diff
            
            int targetLineStart = -1;
            int targetLineEnd = -1;
            if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = pythonDataItem.ParsedDiff.Action;
                targetLineStart = typedParsedDiff.SourceLocations.First();
                targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count();
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // No lines in target required
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = pythonDataItem.ParsedDiff.Action;
                targetLineStart = typedParsedDiff.PreviousSourceLocation + 1;
                targetLineEnd = targetLineStart + typedParsedDiff.TargetLines.Count();
            }

            SyntaxToken[] updatedCodeChunkBlockStmtTokens = new SyntaxToken[] {};
            if (targetLineStart != -1)  // Otherwise no need to tokenize output at all
            {
                var updatedTreeText = updatedFileAst.GetText();
                // var changeSpan = new TextSpan(targetLineStart, targetLineEnd - targetLineStart);

                var updatedCodeChunkNodes = GetNodesByLineSpan(
                    canonicalUpdatedFileAst,
                    updatedCodeFile,
                    targetLineStart,
                    targetLineEnd
                );
                if (updatedCodeChunkNodes.Any(node => !allowedSytaxKinds.Contains(node.Kind())))
                    yield return null;


                var updatedCodeChunkBlockStmt = SyntaxFactory.Block(updatedCodeChunkNodes.Select(node => (StatementSyntax)node));
                updatedCodeChunkBlockStmtTokens = updatedCodeChunkBlockStmt.DescendantTokens().Skip(1).SkipLast(1).ToArray();
            }

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
            // Write all calculated data to JSONObject

            if (pythonDataItem.ParsedDiff.ActionType == "REPLACE")
            {
                ReplaceAction typedParsedDiff = pythonDataItem.ParsedDiff.Action;

                // TODO:
                // Use updatedCodeChunkBlockStmtTextTokens
                // typedParsedDiff.TokenizedTargetLines = 
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "REMOVE")
            {
                // Nothing to tokenize
            }
            else if (pythonDataItem.ParsedDiff.ActionType == "ADD")
            {
                AddAction typedParsedDiff = pythonDataItem.ParsedDiff.Action;

                // TODO:
                // Use updatedCodeChunkBlockStmtTextTokens
                // typedParsedDiff.TokenizedTargetLines = 
            }

            pythonDataItem.TokenizedFileContext = prevCodeChunkBlockStmtTextTokens.ToList();
            //  --> all formatting tokenized as well
            //  --> error token(s) inside

            // TODO:
            // pythonDataItem.DiagnosticOccurances.TokenizedMessage =
            // pythonDataItem.ParsedDiff.Action.TargetLines =

            // TODO: Consider using prevCodeTextChunk to overwrite
            // pythonDataItem.FileContext

            yield return pythonDataItem;



            // -------


            // Previously:

            //var changesInRevision = GetChangesBetweenAsts(canonicalPrevFileAst.SyntaxTree, canonicalUpdatedFileAst.SyntaxTree);

            //// Should only be one change
            //foreach (var change in changesInRevision)
            //{
            //    // The location in terms of path, line and column for a given span.
            //    var prevCodeChunkLineSpan = canonicalPrevFileAst.SyntaxTree.GetLineSpan(change.BeforeSpan.ChangeSpan);
            //    var updatedCodeChunkLineSpan = canonicalUpdatedFileAst.SyntaxTree.GetLineSpan(change.AfterSpan.ChangeSpan);

            //    var prevCodeChunkLineSpanStart = prevCodeFile.Lines[prevCodeChunkLineSpan.StartLinePosition.Line].Span.Start;
            //    var prevCodeChunkSpanEnd = prevCodeFile.Lines[prevCodeChunkLineSpan.EndLinePosition.Line].Span.End;

            //    var updatedCodeChunkLineSpanStart = updatedCodeFile.Lines[updatedCodeChunkLineSpan.StartLinePosition.Line].Span.Start;
            //    var updatedCodeChunkSpanEnd = updatedCodeFile.Lines[updatedCodeChunkLineSpan.EndLinePosition.Line].Span.End;

            //    // only consider changes of equal number of lines
            //    if (prevCodeChunkLineSpan.EndLinePosition.Line - prevCodeChunkLineSpan.StartLinePosition.Line 
            //        != updatedCodeChunkLineSpan.EndLinePosition.Line - updatedCodeChunkLineSpan.StartLinePosition.Line)
            //        continue;

            //    // only consider SyntaxKind in allowedSytaxKinds
            //    var prevCodeChunkNodes = GetNodesByLineSpan(
            //        canonicalPrevFileAst,
            //        prevCodeFile, // Why is this needed?
            //        prevCodeChunkLineSpan.StartLinePosition.Line,
            //        prevCodeChunkLineSpan.EndLinePosition.Line
            //    );
            //    if (prevCodeChunkNodes.Any(node => !allowedSytaxKinds.Contains(node.Kind())))
            //        continue;

            //    var updatedCodeChunkNodes = GetNodesByLineSpan(
            //        canonicalUpdatedFileAst,
            //        updatedCodeFile, 
            //        updatedCodeChunkLineSpan.StartLinePosition.Line,
            //        updatedCodeChunkLineSpan.EndLinePosition.Line
            //    );
            //    if (updatedCodeChunkNodes.Any(node => !allowedSytaxKinds.Contains(node.Kind())))
            //        continue;

            //    // ----
            //    // Only doing this to check for useless changes

            //    var previousCodeChunkTokens = prevTokenIndex
            //        .GetTokensInSpan(prevCodeChunkLineSpanStart, prevCodeChunkSpanEnd)
            //        .Select(token => token.ValueText)
            //        // .Where(token => !string.IsNullOrWhiteSpace(token) && !string.IsNullOrEmpty(token))  // Want to include formatting
            //        .ToArray();

            //    var updatedsCodeChunkTokens = updatedTokenIndex
            //        .GetTokensInSpan(updatedCodeChunkLineSpanStart, updatedCodeChunkSpanEnd)
            //        .Select(token => token.ValueText)
            //        // .Where(token => !string.IsNullOrWhiteSpace(token) && !string.IsNullOrEmpty(token))  // Want to include formatting
            //        .ToArray();

            //    if (!(previousCodeChunkTokens.Length > 0 && updatedsCodeChunkTokens.Length > 0 &&
            //        IsValidCodeChunkTokens(previousCodeChunkTokens) && IsValidCodeChunkTokens(updatedsCodeChunkTokens) &&
            //        !previousCodeChunkTokens.SequenceEqual(updatedsCodeChunkTokens)))
            //    {
            //        continue;
            //    }

            //    // -------

            //    // Create SyntaxBlock out of list of SyntaxNode (probably starts/ends with "{","}")
            //    // Does "StatementSyntax" remove spaces, etc.? 
            //    var prevCodeChunkBlockStmt = SyntaxFactory.Block(prevCodeChunkNodes.Select(node => (StatementSyntax)node));
            //    var updatedCodeChunkBlockStmt = SyntaxFactory.Block(updatedCodeChunkNodes.Select(node => (StatementSyntax)node));

            //    IDictionary<string, string> zeroIndexedVariableNameMap;
            //        (prevCodeChunkBlockStmt, updatedCodeChunkBlockStmt, zeroIndexedVariableNameMap) =
            //        zeroIndexVariableNames(prevCodeChunkBlockStmt, updatedCodeChunkBlockStmt);



            //    // Finished text representation of change (including formatting)
            //    var prevCodeTextChunk = Utils.ExtractCodeTextFromBraces(prevCodeChunkBlockStmt.GetText().ToString());
            //    prevCodeTextChunk = Utils.RemoveLeadingWhiteSpace(prevCodeTextChunk, naive: true);

            //    var updatedCodeTextChunk = Utils.ExtractCodeTextFromBraces(updatedCodeChunkBlockStmt.GetText().ToString());
            //    updatedCodeTextChunk = Utils.RemoveLeadingWhiteSpace(updatedCodeTextChunk, naive: true);



            //    // .Skip(1).SkipLast(1) probably to remove "{","}"
            //    var prevCodeChunkBlockStmtTokens = prevCodeChunkBlockStmt.DescendantTokens().Skip(1).SkipLast(1).ToArray();
            //    var prevCodeChunkBlackStmtTokensIndex = new TokenIndex(prevCodeChunkBlockStmtTokens).InitInvertedIndex();

            //    var updatedCodeChunkBlockStmtTokens = updatedCodeChunkBlockStmt.DescendantTokens().Skip(1).SkipLast(1).ToArray();
            //    var updatedCodeChunkBlockStmtTokensIndex = new TokenIndex(updatedCodeChunkBlockStmtTokens).InitInvertedIndex();



            //    // Build AST representation
            //    var prevCodeBlockJObject = jsonSyntaxTreeHelper.GetJObjectForSyntaxNode(prevCodeChunkBlockStmt, prevCodeChunkBlackStmtTokensIndex);
            //    var updatedCodeBlockJObject = jsonSyntaxTreeHelper.GetJObjectForSyntaxNode(updatedCodeChunkBlockStmt, updatedCodeChunkBlockStmtTokensIndex);

            //    var precedingContextTokens = prevTokenIndex.GetTokensInSpan(change.BeforeSpan.SpanOfPrecedingContext);
            //    var succeedingContextTokens = updatedTokenIndex.GetTokensInSpan(change.BeforeSpan.SpanOfSucceedingContext);

            //    precedingContextTokens = zeroIndexVariableNames(precedingContextTokens, zeroIndexedVariableNameMap);
            //    succeedingContextTokens = zeroIndexVariableNames(succeedingContextTokens, zeroIndexedVariableNameMap);

            //    // Finished list of tokens in the change (without formatting)
            //    var prevCodeChunkBlockStmtTextTokens =
            //        prevCodeChunkBlockStmtTokens.Select(token => token.ValueText).ToArray();
            //    var updatedCodeChunkBlockStmtTextTokens =
            //        updatedCodeChunkBlockStmtTokens.Select(token => token.ValueText).ToArray();

            //    var precedingContextTextTokens = precedingContextTokens.Select(token => token.ValueText).ToArray();
            //    var succeedingContextTextTokens = succeedingContextTokens.Select(token => token.ValueText).ToArray();

            //    var result = new
            //    {
            //        PrevCodeChunk = prevCodeTextChunk,  // Still needed
            //        UpdatedCodeChunk = updatedCodeTextChunk,  // Still needed
            //        PrevCodeChunkTokens = prevCodeChunkBlockStmtTextTokens,  // Still needed
            //        UpdatedCodeChunkTokens = updatedCodeChunkBlockStmtTextTokens,  // Still needed
            //        PrevCodeAST = prevCodeBlockJObject,
            //        UpdatedCodeAST = updatedCodeBlockJObject,
            //        PrecedingContext = precedingContextTextTokens,  // Still needed
            //        SucceedingContext = succeedingContextTextTokens  // Still needed
            //    };

            //    yield return result;
                
            //}
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

            var syntaxHelper = new JsonSyntaxTreeHelper(grammarPath);

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

                        ProcessSingleRevision(pythonDataItem, syntaxHelper);

                        // TODO: Write pythonDataItem to file again

                        System.Environment.Exit(1);
                        break;

                    }
                }
                catch (Exception e) {
                    Console.WriteLine($"e: {e}");
                }
            }

            //using (var fs = File.Open(outputFilePath, FileMode.Create))
            //using(var sw = new StreamWriter(fs, Encoding.UTF8))
            //{
            //    Stopwatch stopwatch = new Stopwatch();
            //    stopwatch.Start();
            //    foreach (var changeStrs in ReadRevisionData(revisionDataFilePath).AsParallel().Select(x =>
            //        ProcessSingleRevision(x, syntaxHelper).Select(t => changeEntryDatumToJsonString(t)).ToArray()))
            //    {
            //        foreach (var changeStr in changeStrs)
            //        {
            //            try
            //            {
            //                sw.WriteLine(changeStr);
            //            }
            //            catch (Exception e) { }
            //        }

            //    }

            //    stopwatch.Stop();
            //    Console.WriteLine();
            //    Console.WriteLine("Time elapsed: {0}", stopwatch.Elapsed);
            //}
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

        static readonly HashSet<SyntaxKind> allowedSytaxKinds = new HashSet<SyntaxKind>()
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
