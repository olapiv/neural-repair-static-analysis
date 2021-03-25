using System;
using System.Reflection;

namespace InfoExtractor
{
    public class DiagnosticInfoAsCSV
    {
        public DiagnosticInfoAsCSV(
            Assembly assembly,
            String type,
            String diagnosticID
        )
        {
            // TODO: Get package here
            this.assembly = assembly.GetName().Name;
            this.type = type;
            this.diagnosticID = diagnosticID;
        }

        public String package;
        public String assembly;
        public String type;  // TODO: Use Enum
        public String diagnosticID;

        // ANALYZER_PACKAGE,ANALYZER_ASSEMBLY,TYPE,DIAGNOSTIC_ID
    }
}
