using System;
using System.Reflection;

namespace InfoExtractor
{
    public class DiagnosticInfoAsCSV
    {

        public DiagnosticInfoAsCSV(
            String packageName,
            Assembly assembly,
            String type,
            String diagnosticID,
            String diagnosticTitle = null,
            String diagnosticDescription = null,
            String diagnosticDefaultSeverity = null,
            String diagnosticCategory = null,
            String diagnosticCustomTags = null,
            String refactoringName = null
        )
        {
            this.NuGetAnalyzerPackage = packageName;
            this.AssemblyName = assembly.GetName().Name;
            this.Type = type;
            this.DiagnosticID = diagnosticID;
            this.DiagnosticTitle = diagnosticTitle;
            this.DiagnosticDescription = diagnosticDescription;
            this.DiagnosticDefaultSeverity = diagnosticDefaultSeverity;
            this.DiagnosticCategory = diagnosticCategory;
            this.DiagnosticCustomTags = diagnosticCustomTags;
            this.RefactoringName = refactoringName;
        }

        public String NuGetAnalyzerPackage { get; set; }
        public String AssemblyName { get; set; }
        public String Type { get; set; }
        public String DiagnosticID { get; set; }
        public String DiagnosticTitle { get; set; }
        public String DiagnosticDescription { get; set; }
        public String DiagnosticDefaultSeverity { get; set; }
        public String DiagnosticCategory { get; set; }
        public String DiagnosticCustomTags { get; set; }
        public String RefactoringName { get; set; }

    }
}
