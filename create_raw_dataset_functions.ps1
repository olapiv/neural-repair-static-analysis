
$ROSLYNATOR = "C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe"
$MS_BUILD_PATH = 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin'


function GetAllRepoSolutions{
    param (
        $REPO_PATH
    )
    $SOLUTION_FILES = Get-Childitem -File -force -Recurse -Include *.sln -Path $REPO_PATH |
        Foreach-Object {
            $FILENAME = $_.Name
            $DIRECTORY = $_.Directory
            @{ Filename = $FILENAME; Filepath = "$DIRECTORY/$FILENAME" }
    return $SOLUTION_FILES
}


function ApplyRoslynatorAnalysis {
    param (
        $ANALYSIS_FILEPATH,
        $SOLUTION_OR_PROJECT_FILEPATH,
        $NUGET_PATH
    )
    
    Write-Output "Creating ANALYSIS_FILEPATH: $ANALYSIS_FILEPATH"

    Write-Output "
        roslynator analyze
            --msbuild-path $MS_BUILD_PATH
            $SOLUTION_FILEPATH
            -v quiet
            --output $ANALYSIS_FILEPATH
            --report-not-configurable
            --ignore-analyzer-references
            --analyzer-assemblies $NUGET_PATH
        "

    C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe analyze `
    --msbuild-path $MS_BUILD_PATH `
    $SOLUTION_FILEPATH `
    --output $ANALYSIS_FILEPATH `
    --report-not-configurable `
    --ignore-analyzer-references `
    --analyzer-assemblies $NUGET_PATH
    # -v quiet `
    # report-not-configurable: Mostly compiler diagnostics (CSxxxx)
    # ignore-analyzer-references: Only use our own analyzer assemblies

}


function ApplyRoslynatorFix {
    param (
        $SOLUTION_OR_PROJECT_FILEPATH,
        $NUGET_PATH,
        $DIAGNOSTIC_ID
    )

    Write-Output "
        roslynator fix
            --msbuild-path $MS_BUILD_PATH
            $SOLUTION_OR_PROJECT_FILEPATH
            --ignore-analyzer-references
            --analyzer-assemblies $NUGET_PATH
            --supported-diagnostics $DIAGNOSTIC_ID
        "

    # This basically produces a diff
    C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe fix `
        --msbuild-path $MS_BUILD_PATH `
        $SOLUTION_OR_PROJECT_FILEPATH `
        --ignore-analyzer-references `
        --analyzer-assemblies $NUGET_PATH `
        --supported-diagnostics $DIAGNOSTIC_ID

}

function SaveRoslynatorFixDiff {
    param (
        $FIXED_REPO_PATH
        $DIFF_FILEPATH
    )
    $CURRENT_DIR = $PWD

    cd $FIXED_REPO_PATH
    $DIFF_CONTENT = $(git diff)

    if ( "$DIFF_CONTENT" -eq "" ) {
        Write-Output "Empty diff!"
    }
    else {
        Write-Output "Creating DIFF_FILEPATH: $DIFF_FILEPATH"
        if (!(Test-Path $DIFF_FILEPATH)) {
            [void](New-Item -ItemType "file" -Path $DIFF_FILEPATH)
        }
        $DIFF_CONTENT > $DIFF_FILEPATH
        git reset --hard
    }

    cd $CURRENT_DIR
}

function RunAndSaveFix {
    param (
        $SOLUTION_FILEPATH,
        $NUGET_FULL_NAME,
        $NUGET_PATH,
        $OUTPUT_FILENAME,
        $OUTPUT_DIR,
        $ANALYZER_PACKAGE_DETAILS_ROW  # from analyzer_package_details.csv
    )

    # TODO: Iterate over ANALYZER_PACKAGE_DETAILS here and check whether there is CODEFIX_PROVIDER available

    if ($NUGET_FULL_NAME -ne $ANALYZER_PACKAGE_DETAILS_ROW.HostingPackageName ) {
        continue
    }

    if ($ANALYZER_PACKAGE_DETAILS_ROW.Type -ne "CODEFIX_PROVIDER") {
        continue
    }

    $DIAGNOSTIC_ID = $ANALYZER_PACKAGE_DETAILS_ROW.DiagnosticID
    Write-Output "Applying fix with DIAGNOSTIC_ID: $DIAGNOSTIC_ID"
    
    ApplyRoslynatorFix
        --SOLUTION_OR_PROJECT_FILEPATH $SOLUTION_FILEPATH
        --NUGET_PATH $NUGET_PATH
        --DIAGNOSTIC_ID $DIAGNOSTIC_ID

    $DIFF_FILENAME = "${OUTPUT_FILENAME}__${DIAGNOSTIC_ID}.diff"
    $DIFF_FILEPATH = "$OUTPUT_DIR/$DIFF_FILENAME"

    SaveRoslynatorFixDiff
        --FIXED_REPO_PATH $REPO_PATH
        --DIFF_FILEPATH $DIFF_FILEPATH
    
}