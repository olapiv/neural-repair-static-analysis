# More efficient analysis dataset gathering: apply all analyzers of 
# one Nuget package on a C# Solution; The resulting output will show
# which diagnostic resulted into which error message. This only works
# with analysis and not with fixers.

# Create folders if not exist:
$null = [System.IO.Directory]::CreateDirectory('./raw_dataset/efficient/analysis_files')

$ROSLYNATOR = "C:\Users\vlohse\.nuget\packages\roslynator.commandline\0.1.1\tools\net48\Roslynator.exe"
$MS_BUILD_PATH = 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin'

$CLONED_REPOS_DIR = "./cloned_repos_to_analyze"
$CURRENT_DIR = $PWD
Write-Output "CURRENT_DIR: $CURRENT_DIR"

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

    $REPO_TO_ANALYZE = "$CLONED_REPOS_DIR/$REPO_NAME"

    Write-Output "Cloning: $REPO_NAME"
    git clone $REPO_URL $REPO_TO_ANALYZE

    cd $REPO_TO_ANALYZE
    $LAST_COMMIT = $(git log -n 1 --pretty=format:"%H")
    Write-Output "Last commit: $LAST_COMMIT"
    cd "$CURRENT_DIR"

    Write-Output "REPO_TO_ANALYZE: $REPO_TO_ANALYZE"

    # TODO: Ask Niklas: use -Exclude */libraries/* ?
    # $SOLUTION_FILES = Get-Childitem -File -force -Recurse -Include *.sln -Path "/Users/vincent/not_in_cloud/Codes/KTH/acr-static-analysis-code/cloned_repos_to_analyze/runtime/src/libraries/Microsoft.Extensions.Caching.Memory" |
    $SOLUTION_FILES = Get-Childitem -File -force -Recurse -Include *.sln -Path $REPO_TO_ANALYZE |
    Foreach-Object {
        $FILENAME = $_.Name
        $DIRECTORY = $_.Directory
        @{ Filename = $FILENAME; Filepath = "$DIRECTORY/$FILENAME" }
    }

    $NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
    Write-Output "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    foreach ($SOLUTION_FILE in $SOLUTION_FILES) {

        $SOLUTION_FILENAME = $SOLUTION_FILE.Filename
        $SOLUTION_FILEPATH = $SOLUTION_FILE.Filepath
        Write-Output "Working with SOLUTION_FILENAME: $SOLUTION_FILENAME"

        foreach ($ANALYZER_PACKAGE in $ANALYZER_PACKAGES) {

            $NUGET_FULL_NAME = $ANALYZER_PACKAGE.NugetFullname
            $NUGET_PATH = $ANALYZER_PACKAGE.NugetPath

            if (-Not ($RELEVANT_ANALYZER_PACKAGES.Contains($NUGET_FULL_NAME))) {
                continue
            }
            Write-Output "Using NuGet package: $NUGET_FULL_NAME"

            $OUTPUT_FILENAME = "${REPO_NAME}__${SOLUTION_FILENAME}__${LAST_COMMIT}__${NUGET_FULL_NAME}"
            Write-Output "Creating OUTPUT_FILENAME: $OUTPUT_FILENAME"

            $ANALYSIS_FILEPATH = "./raw_dataset/efficient/analysis_files/${OUTPUT_FILENAME}.xml"
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

                # break
        }
        # break
    }
    # break
}
