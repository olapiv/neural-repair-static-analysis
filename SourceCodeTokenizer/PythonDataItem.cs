using System;
using System.Collections.Generic;
using Newtonsoft.Json;


namespace SourceCodeTokenizer
{
    public class PythonDataItem
    {
        public string Repo;
        public string RepoURL;
        public string SolutionFile;
        public string FilePath;
        public int NumberFileLines;
        public string Commit;
        public string FileURL;
        public string DiagnosticID;
        public string AnalyzerNuGet;
        public string Severity;
        public List<DiagnosticOccurance> DiagnosticOccurances;
        public ParsedDiff ParsedDiff;
        public string FileContextStart;
        public List<string> FileContext;

        // TODO: Add this in Python
        public int requiredLinesStart;
        public int requiredLinesEnd;

        public List<string> TokenizedFileContext;  // TODO: Fill this

        // public PythonDataItem(){}
    }

    public class DiagnosticOccurance
    {
        public string Message;
        public int Line;
        public int Character;
        public List<string> TokenizedMessage;  // TODO: Fill this
    }

    public class ParsedDiff
    {
        public string ActionType;
        public dynamic Action;
    }

    public class AddAction
    {
        public int PreviousSourceLocation;
        public int TargetStartLocation;
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // TODO: Fill this
    }

    public class ReplaceAction
    {
        public int[] SourceLocations;
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // TODO: Fill this
    }

    public class RemoveAction
    {
        public int SourceLocationStart;
        public int SourceLocationEnd;
    }

    //public class TokenizedDataItem : PythonDataItem
    //{
    //    public string TokenizedFileContext;
    //}

}
