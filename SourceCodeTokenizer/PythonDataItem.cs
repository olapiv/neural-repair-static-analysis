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

        //public string TokenizedFileContext;

        //public PythonDataItem(){}
    }

    public class DiagnosticOccurance
    {
        public string Message;
        public int Line;
        public int Character;
        //public string TokenizedMessage;
    }

    public class ParsedDiff
    {
        public string ActionType;
        public dynamic Action;
    }

    //public class TokenizedDataItem : PythonDataItem
    //{
    //    public string TokenizedFileContext;
    //}
}
