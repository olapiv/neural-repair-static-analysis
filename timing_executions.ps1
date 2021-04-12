

# Create folders if not exist:
$null = [System.IO.Directory]::CreateDirectory('./raw_dataset/timing_analysis')

$ROSLYNATOR = "C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe"
$MS_BUILD_PATH = 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin'

$NUGET_FULL_NAME = "AgodaAnalyzers.1.0.517"
$NUGET_PATH = "nuget_analyzer_packages/AgodaAnalyzers.1.0.517"

$CLONED_REPOS_DIR = "./cloned_repos_to_analyze"
$REPO_NAME = "runtime"
$REPO_URL = "https://github.com/dotnet/runtime.git"
$REPO_TO_ANALYZE = "$CLONED_REPOS_DIR/$REPO_NAME"

function ExecuteRoslynatorOnProjOrSol {
    param (
        $REPO_NAME,
        $SOLUTION_FILENAME,
        $SOLUTION_FILEPATH
    )

    Write-Output "Working with SOLUTION_FILENAME: $SOLUTION_FILENAME"

    $OUTPUT_FILENAME = "${REPO_NAME}__${SOLUTION_FILENAME}__${NUGET_FULL_NAME}"
    $ANALYSIS_FILEPATH = "./raw_dataset/timing_analysis/${OUTPUT_FILENAME}.xml"
    Write-Output "Creating ANALYSIS_FILEPATH: $ANALYSIS_FILEPATH"

    Write-Output "
    roslynator analyze
        --msbuild-path $MS_BUILD_PATH
        $SOLUTION_FILEPATH
        -v quiet
        --output $ANALYSIS_FILEPATH
        --report-not-configurable
        --ignore-analyzer-references
        --analyzer-assemblies $NUGET_PATH `n"

    # C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe analyze `
    #     --msbuild-path $MS_BUILD_PATH `
    #     $SOLUTION_FILEPATH `
    #     --output $ANALYSIS_FILEPATH `
    #     --report-not-configurable `
    #     --ignore-analyzer-references `
    #     --analyzer-assemblies $NUGET_PATH
    #     # -v quiet `
    #     # report-not-configurable: Mostly compiler diagnostics (CSxxxx)
    #     # ignore-analyzer-references: Only use our own analyzer assemblies

}

Write-Output "Cloning: $REPO_NAME"
git clone $REPO_URL $REPO_TO_ANALYZE

### ---------------------------------------------

# $SOLUTION_FILES = Get-Childitem -File -force -Recurse -Include *.sln -Path "/Users/vincent/not_in_cloud/Codes/KTH/acr-static-analysis-code/cloned_repos_to_analyze/runtime/src/libraries/Microsoft.Extensions.Caching.Memory" |
$SOLUTION_FILES = Get-Childitem -File -force -Recurse -Include *.sln -Path $REPO_TO_ANALYZE |
Foreach-Object {
    $FILENAME = $_.Name
    $DIRECTORY = $_.Directory
    @{ Filename = $FILENAME; Filepath = "$DIRECTORY/$FILENAME" }
}

$NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
Write-Output "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"

$sw = [Diagnostics.Stopwatch]::StartNew()

foreach ($SOLUTION_FILE in $SOLUTION_FILES) {
    $SOLUTION_FILENAME = $SOLUTION_FILE.Filename
    $SOLUTION_FILEPATH = $SOLUTION_FILE.Filepath
    ExecuteRoslynatorOnProjOrSol -SOLUTION_FILENAME $SOLUTION_FILENAME -SOLUTION_FILEPATH $SOLUTION_FILEPATH
    break
}

$sw.Stop()
$ELAPSED_MINUTES = $sw.Elapsed.TotalMinutes
Write-Output "ELAPSED_MINUTES: $ELAPSED_MINUTES"

$RESULT = "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS; ELAPSED_MINUTES: $ELAPSED_MINUTES;"
$TIMER_RESULTS_PATH = "./TIMED__PER_SOLUTION__${REPO_NAME}__${NUGET_FULL_NAME}.txt"
if (!(Test-Path $TIMER_RESULTS_PATH)) {
    [void](New-Item -ItemType "file" -Path $TIMER_RESULTS_PATH)
}
$RESULT > $TIMER_RESULTS_PATH

$sw = [Diagnostics.Stopwatch]::StartNew()

### ---------------------------------------------

$PROJECT_FILES = Get-Childitem -File -force -Recurse -Include *.csproj -Path $REPO_TO_ANALYZE |
Foreach-Object {
    $FILENAME = $_.Name
    $DIRECTORY = $_.Directory
    @{ Filename = $FILENAME; Filepath = "$DIRECTORY/$FILENAME" }
}

$NUMBER_PROJECTS = $PROJECT_FILES.Count
Write-Output "NUMBER_PROJECTS: $NUMBER_PROJECTS"

foreach ($PROJECT_FILE in $PROJECT_FILES) {
    $PROJECT_FILENAME = $PROJECT_FILE.Filename
    $PROJECT_FILEPATH = $PROJECT_FILE.Filepath
    ExecuteRoslynatorOnProjOrSol -SOLUTION_FILENAME $PROJECT_FILENAME -SOLUTION_FILEPATH $PROJECT_FILEPATH
    break
}

$sw.Stop()
$ELAPSED_MINUTES = $sw.Elapsed.TotalMinutes
Write-Output "ELAPSED_MINUTES: $ELAPSED_MINUTES"

$RESULT = "NUMBER_PROJECTS: $NUMBER_PROJECTS; ELAPSED_MINUTES: $ELAPSED_MINUTES;"
$TIMER_RESULTS_PATH = "./TIMED__PER_PROJECT__${REPO_NAME}__${NUGET_FULL_NAME}.txt"
if (!(Test-Path $TIMER_RESULTS_PATH)) {
    [void](New-Item -ItemType "file" -Path $TIMER_RESULTS_PATH)
}
$RESULT > $TIMER_RESULTS_PATH