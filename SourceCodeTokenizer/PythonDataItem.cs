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
        public List<DiagnosticOccurance> DiagnosticOccurances;
        public ParsedDiff ParsedDiff;
        public string FileContextStart;
        public List<string> FileContext;

        public int RequiredLinesStart;
        public int RequiredLinesEnd;

        public List<string> TokenizedFileContext;  // Fill out in Pipeline

        public void RemoveOldData()
        {
            foreach (var diagOccurance in this.DiagnosticOccurances)
            {
                diagOccurance.Message = null;
            }
            try
            {
                this.ParsedDiff.Action.TargetLines = null;
            }
            catch (RuntimeBinderException)
            {
                //  TargetLines not in this.ParsedDiff.Action
            }

            this.Repo = null;
            this.RepoURL = null;
            this.SolutionFile = null;
            this.FilePath = null;
            this.Commit = null;
            this.AnalyzerNuGet = null;
            this.FileContextStart = null;
            this.FileContext = null;

            return;
        }
    }

    public class DiagnosticOccurance
    {
        public string Message;
        public int Line;
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
        public int PreviousSourceLocation;
        public int TargetStartLocation;
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // Fill out in Pipeline
    }

    public class ReplaceAction
    {
        public int[] SourceLocations;
        public string[] TargetLines;
        public string[] TokenizedTargetLines;  // Fill out in Pipeline
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
