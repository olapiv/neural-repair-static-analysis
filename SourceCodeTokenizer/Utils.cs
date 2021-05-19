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
    public class Utils
    {
        public Utils()
        {
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
            }
            else if (parsedDiff.ActionType == "ADD")
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

        public static IEnumerable<String> GetTriviaByLineSpan(SyntaxNode astNode, int startLine, int endLine)
        {
            startLine--;
            endLine--;

            var allDescendentTrivia = new List<SyntaxTrivia>();
            foreach (var descTrivia in astNode.DescendantTrivia())
            {
                Utils.FlattenDescendentTrivia(allDescendentTrivia, descTrivia);
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

        public static List<SyntaxToken> AddContextTokensToListOfTokens(
            List<SyntaxToken> coreTokenList,
            List<SyntaxToken> allTokensList,
            int startPosition,
            int endPosition,
            int missingTokens
        )
        {

            // Add context tokens until NUM_INPUT_TOKENS is reached

            SyntaxToken beforeToken, afterToken;
            while (missingTokens > 0)
            {
                if (startPosition == 0 && endPosition == allTokensList.Count())
                {
                    break;
                }

                // Switch between prepending and appending tokens
                if (
                    startPosition == 0 ||
                    missingTokens % 2 == 1
                )
                {
                    endPosition++;
                    afterToken = allTokensList[endPosition];
                    coreTokenList.Add(afterToken);
                }
                else if (
                  endPosition == allTokensList.Count() ||
                  missingTokens % 2 == 0
              )
                {
                    startPosition--;
                    beforeToken = allTokensList[startPosition];
                    coreTokenList.Insert(0, beforeToken);
                }

                missingTokens--;
            }

            return coreTokenList;
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
            }
            else
            {
                triviaList.Add(trivia);
            }
            return triviaList;
        }
    }
}
