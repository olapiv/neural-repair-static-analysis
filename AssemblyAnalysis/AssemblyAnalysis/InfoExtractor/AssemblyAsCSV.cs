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
            String diagnosticID
        )
        {
            this.HostingPackageName = packageName;
            this.AssemblyName = assembly.GetName().Name;
            this.Type = type;
            this.DiagnosticID = diagnosticID;
        }

        //public static class DiagnosticType
        //{
        //    public const string
        //        DiagnosticAnalyzer = "DIAGNOSTIC_ANALYZER",
        //        CodefixProvider = "CODEFIX_PROVIDER";
        //}

        public String HostingPackageName { get; set; }
        public String AssemblyName { get; set; }
        public String Type { get; set; }
        public String DiagnosticID { get; set; }

        // ANALYZER_PACKAGE,ANALYZER_ASSEMBLY,TYPE,DIAGNOSTIC_ID
    }
}
