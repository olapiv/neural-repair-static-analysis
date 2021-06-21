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
            String diagnosticCategory = null
            // String diagnosticCustomTags = null
        )
        {
            this.HostingPackageName = packageName;
            this.AssemblyName = assembly.GetName().Name;
            this.Type = type;
            this.DiagnosticID = diagnosticID;

            this.diagnosticTitle = diagnosticTitle;
            this.diagnosticDescription = diagnosticDescription;
            this.diagnosticCategory = diagnosticCategory;
            // this.diagnosticCustomTags = diagnosticCustomTags;
        }

        public String HostingPackageName { get; set; }
        public String AssemblyName { get; set; }
        public String Type { get; set; }
        public String DiagnosticID { get; set; }
        public String diagnosticTitle { get; set; }
        public String diagnosticDescription { get; set; }
        public String diagnosticCategory { get; set; }
        // public String diagnosticCustomTags { get; set; }

        // ANALYZER_PACKAGE,ANALYZER_ASSEMBLY,TYPE,DIAGNOSTIC_ID
    }
}
