using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Microsoft.CSharp.RuntimeBinder;


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
        public List<DiagnosticOccurance> DiagnosticOccurances;  // Adjust out in Pipeline
        public ParsedDiff ParsedDiff;  // Adjust out in Pipeline
        public Nullable<int> FileContextStart;
        public List<string> FileContext;
        public Nullable<int> RequiredLinesStart;
        public Nullable<int> RequiredLinesEnd;
        public List<string> TokenizedFileContext;  // Fill out in Pipeline

        public void RemoveOldData()
        {
            foreach (var diagOccurance in this.DiagnosticOccurances)
            {
                // diagOccurance.Message = null;
            }
            if (this.ParsedDiff.ActionType != "REMOVE")
            {
                // this.ParsedDiff.Action.TargetLines = null;

                if (this.ParsedDiff.ActionType == "ADD")
                {
                    this.ParsedDiff.Action.TargetStartLocation = null;
                }
            }

            this.Repo = null;
            this.RepoURL = null;
            this.SolutionFile = null;
            this.FilePath = null;
            this.Commit = null;
            this.AnalyzerNuGet = null;
            this.FileContextStart = null;
            this.RequiredLinesStart = null;
            this.RequiredLinesEnd = null;
            // this.FileContext = null;

            return;
        }
    }

    public class DiagnosticOccurance
    {
        public string Message;
        public int Line;  // Subtract offset in Pipeline (?)
        public int Character;
        public List<string> TokenizedMessage;  // Fill out in Pipeline
    }

    public class ParsedDiff
    {
        public string ActionType;
        public dynamic Action;
    }

    public class AddAction
    {
        public int PreviousSourceLocation;  // Subtract offset in Pipeline
        public Nullable<int> TargetStartLocation;
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // Fill out in Pipeline
    }

    public class ReplaceAction
    {
        public int[] SourceLocations;  // Subtract offset in Pipeline
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // Fill out in Pipeline
    }

    public class RemoveAction
    {
        public int SourceLocationStart;  // Subtract offset in Pipeline
        public int SourceLocationEnd;  // Subtract offset in Pipeline
    }

}
