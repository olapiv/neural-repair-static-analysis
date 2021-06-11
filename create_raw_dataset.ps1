
$CURRENT_DIR = $PWD
$OUTPUT_DIR_FIX = "$CURRENT_DIR/raw_dataset/diffs"
$OUTPUT_DIR_ANALYSIS = "$CURRENT_DIR/raw_dataset/analysis_files"
$SUBMODULE_REPOS_DIR = "./submodule_repos_to_analyze"
$OUTPUT_DIR_TIMINGS = "$CURRENT_DIR/raw_dataset/timings"

# Create folders if not exist:
$null = [System.IO.Directory]::CreateDirectory($OUTPUT_DIR_ANALYSIS)
$null = [System.IO.Directory]::CreateDirectory($OUTPUT_DIR_FIX)
$null = [System.IO.Directory]::CreateDirectory($OUTPUT_DIR_TIMINGS)

. ./create_raw_dataset_functions.ps1

$ANALYZER_PACKAGES = Get-Childitem -Path nuget_analyzer_packages/* |
Foreach-Object {
    @{ NugetFullname = $_.Name; NugetPath = $_.FullName }
}
# $ANALYZER_PACKAGES = @(@{ NugetFullname = "Agoda.Analyzers.1.0.517"; NugetPath = "C:\Users\vlohse\Desktop\neural-repair-static-analysis\nuget_analyzer_packages\Agoda.Analyzers.1.0.517" })
Write-Output "Loaded ANALYZER_PACKAGES"

$ANALYZER_PACKAGE_DETAILS = Import-Csv -Path "analyzer_package_details_filtered.csv"
Write-Output "Loaded ANALYZER_PACKAGE_DETAILS"

[string[]]$RELEVANT_ANALYZER_PACKAGES = Get-Content -Path ./nuget_packages_relevant_sources.txt

$GH_REPOS = Import-Csv -Path "github_repos.csv"
$GH_REPOS | ForEach-Object -ThrottleLimit 10 -Parallel {

    $REPO_NAME = $_.RepoName
    $REPO_URL = $_.RepoURL

    $REPO_PATH = "$Using:SUBMODULE_REPOS_DIR/$REPO_NAME"

    Write-Output "Adding submodule: $REPO_NAME"
    git submodule add $REPO_URL $REPO_PATH

    cd $REPO_PATH
    $LAST_COMMIT = $(git log -n 1 --pretty=format:"%H")
    Write-Output "Last commit: $LAST_COMMIT"
    cd "$Using:CURRENT_DIR"

    Write-Output "REPO_PATH: $REPO_PATH"

    # Doing this again because the functions cannot be read in parallel otherwise (?)
    . ./create_raw_dataset_functions.ps1

    $SOLUTION_FILES = GetAllRepoSolutions $REPO_PATH

    $NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
    Write-Output "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"

    $swTotal = [Diagnostics.Stopwatch]::StartNew()

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    # $SOLUTION_FILES | ForEach-Object -ThrottleLimit 10 -Parallel {
    foreach ($SOLUTION_FILE in $SOLUTION_FILES) {

        $SOLUTION_FILENAME = $SOLUTION_FILE.Filename
        $SOLUTION_FILEPATH = $SOLUTION_FILE.Filepath

        Write-Output "Working with SOLUTION_FILENAME: $SOLUTION_FILENAME"

        # Necessary because otherwise .Contains() cannot be run
        $RELEVANT_ANALYZER_PACKAGES_COPY = $Using:RELEVANT_ANALYZER_PACKAGES

        foreach ($ANALYZER_PACKAGE in $Using:ANALYZER_PACKAGES) {

            $NUGET_FULL_NAME = $ANALYZER_PACKAGE.NugetFullname
            $NUGET_PATH = $ANALYZER_PACKAGE.NugetPath

            if (-Not ($RELEVANT_ANALYZER_PACKAGES_COPY.Contains($NUGET_FULL_NAME))) {
                continue
            }
            Write-Output "<<<$SOLUTION_FILENAME>>> Using NuGet package: $NUGET_FULL_NAME"

            $OUTPUT_FILENAME = "${REPO_NAME}__${SOLUTION_FILENAME}__${LAST_COMMIT}__${NUGET_FULL_NAME}"

            $ANALYSIS_FILEPATH = "$Using:OUTPUT_DIR_ANALYSIS/${OUTPUT_FILENAME}.xml"
            ApplyRoslynatorAnalysis `
                $ANALYSIS_FILEPATH `
                $SOLUTION_FILEPATH `
                $NUGET_PATH

            if (!(Test-Path $ANALYSIS_FILEPATH)) {
                Write-Output "<<<$SOLUTION_FILENAME>>> No analysis generated for $ANALYSIS_FILEPATH. Skipping fixes"
                continue
            }

            # Get all diagnostic ids which generated a diagnostic on the solution
            [XML]$ANALYSIS_XML = Get-Content $ANALYSIS_FILEPATH
            $DIAGNOSTIC_IDS = $ANALYSIS_XML.Roslynator.CodeAnalysis.Summary.Diagnostic |
                Foreach-Object {
                    $_.Id
                }
        
            # Breaking down diffs into single diagnostics;
            foreach($DIAGNOSTIC_ID in $DIAGNOSTIC_IDS){

                RunAndSaveFix `
                    $REPO_PATH `
                    $SOLUTION_FILEPATH `
                    $NUGET_FULL_NAME `
                    $NUGET_PATH `
                    $OUTPUT_FILENAME `
                    $Using:OUTPUT_DIR_FIX `
                    $Using:ANALYZER_PACKAGE_DETAILS `
                    $DIAGNOSTIC_ID

                # break
            }
            # break
        }
        # break

    }

    $swTotal.Stop()
    $ELAPSED_MINUTES = $swTotal.Elapsed.TotalMinutes
    $NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
    $RESULT = "ELAPSED_MINUTES: $ELAPSED_MINUTES, NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"
    $TIMER_RESULTS_PATH = "$Using:OUTPUT_DIR_TIMINGS/ALL_SOLUTIONS__${REPO_NAME}.txt"
    if (!(Test-Path $TIMER_RESULTS_PATH)) {
        [void](New-Item -ItemType "file" -Path $TIMER_RESULTS_PATH)
    }
    $RESULT > $TIMER_RESULTS_PATH

    # break
}
