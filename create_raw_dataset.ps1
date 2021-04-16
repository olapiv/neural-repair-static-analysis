
$CURRENT_DIR = $PWD
$OUTPUT_DIR_FIX = "$CURRENT_DIR/raw_dataset/diffs"
$OUTPUT_DIR_ANALYSIS = "$CURRENT_DIR/raw_dataset/analysis_files"
$CLONED_REPOS_DIR = "./cloned_repos_to_analyze"

# Create folders if not exist:
$null = [System.IO.Directory]::CreateDirectory($OUTPUT_DIR_ANALYSIS)
$null = [System.IO.Directory]::CreateDirectory($OUTPUT_DIR_FIX)

. ./create_raw_dataset_functions.ps1

$ANALYZER_PACKAGES = Get-Childitem -Path nuget_analyzer_packages/* |
Foreach-Object {
    @{ NugetFullname = $_.Name; NugetPath = $_.FullName }
}
Write-Output "Loaded ANALYZER_PACKAGES"

$ANALYZER_PACKAGE_DETAILS = Import-Csv -Path "analyzer_package_details_filtered.csv"
Write-Output "Loaded ANALYZER_PACKAGE_DETAILS"

[string[]]$RELEVANT_ANALYZER_PACKAGES = Get-Content -Path ./nuget_packages_relevant_sources.txt

$GH_REPOS = Import-Csv -Path "github_repos.csv"
foreach ($GH_REPO_LINE in $GH_REPOS) {
    $REPO_NAME = $GH_REPO_LINE.RepoName
    $REPO_URL = $GH_REPO_LINE.RepoURL

    $REPO_PATH = "$CLONED_REPOS_DIR/$REPO_NAME"

    Write-Output "Cloning: $REPO_NAME"
    git clone $REPO_URL $REPO_PATH

    cd $REPO_PATH
    $LAST_COMMIT = $(git log -n 1 --pretty=format:"%H")
    Write-Output "Last commit: $LAST_COMMIT"
    cd "$CURRENT_DIR"

    Write-Output "REPO_PATH: $REPO_PATH"

    $SOLUTION_FILES = GetAllRepoSolutions $REPO_PATH

    $NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
    Write-Output "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    $SOLUTION_FILES | ForEach-Object -ThrottleLimit 6 -Parallel {

        # Doing this again because the functions cannot be read in parallel otherwise (?)
        . ./create_raw_dataset_functions.ps1

        $SOLUTION_FILENAME = $_.Filename
        $SOLUTION_FILEPATH = $_.Filepath

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

            $OUTPUT_FILENAME = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}"

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

    # break
}
