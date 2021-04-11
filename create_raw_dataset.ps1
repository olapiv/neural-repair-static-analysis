

# Create folders if not exist:
$null = [System.IO.Directory]::CreateDirectory('./raw_dataset/analysis_files')
$null = [System.IO.Directory]::CreateDirectory('./raw_dataset/diffs')

$CLONED_REPOS_DIR="./cloned_repos_to_analyze"
$CURRENT_DIR=$PWD
Write-Output "CURRENT_DIR: $CURRENT_DIR"

$ANALYZER_PACKAGES = Get-Childitem –Path nuget_analyzer_packages/* |
    Foreach-Object {
        $FILENAME = $_.Name
        $DIRECTORY = $_.Directory
        @{ NugetFullname = $FILENAME; NugetPath = "$DIRECTORY/$FILENAME"}
    }
Write-Output "Loaded ANALYZER_PACKAGES"

$ANALYZER_PACKAGE_DETAILS = Import-Csv -Path "analyzer_package_details_filtered.csv"
Write-Output "Loaded ANALYZER_PACKAGE_DETAILS"

$GH_REPOS = Import-Csv -Path "github_repos.csv"
foreach ($GH_REPO_LINE in $GH_REPOS)
{
    $REPO_NAME = $GH_REPO_LINE.RepoName
    $REPO_URL = $GH_REPO_LINE.RepoURL

    $REPO_TO_ANALYZE="$CLONED_REPOS_DIR/$REPO_NAME"

    Write-Output "Cloning: $REPO_NAME"
    git clone $REPO_URL $REPO_TO_ANALYZE

    cd $REPO_TO_ANALYZE
    $LAST_COMMIT=$(git log -n 1 --pretty=format:"%H")
    Write-Output "Last commit: $LAST_COMMIT"
    cd "$CURRENT_DIR"

    Write-Output "REPO_TO_ANALYZE: $REPO_TO_ANALYZE"

    # TODO: Ask Niklas: use -Exclude */libraries/* ?
    # $SOLUTION_FILES = Get-Childitem -File –force -Recurse -Include *.sln –Path $REPO_TO_ANALYZE |
    $SOLUTION_FILES = Get-Childitem -File –force -Recurse -Include *.sln –Path "/Users/vincent/not_in_cloud/Codes/KTH/acr-static-analysis-code/cloned_repos_to_analyze/runtime/src/libraries/Microsoft.Extensions.Caching.Memory" |
        Foreach-Object {
            $FILENAME = $_.Name
            $DIRECTORY = $_.Directory
            @{ Filename = $FILENAME; Filepath = "$DIRECTORY/$FILENAME"}
        }

    $NUMBER_SOLUTIONS = $SOLUTION_FILES.Count
    Write-Output "NUMBER_SOLUTIONS: $NUMBER_SOLUTIONS"

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    foreach ($SOLUTION_FILE in $SOLUTION_FILES){

        $SOLUTION_FILENAME = $SOLUTION_FILE.Filename
        Write-Output "Working with SOLUTION_FILENAME: $SOLUTION_FILENAME"

        foreach ($ANALYZER_PACKAGE in $ANALYZER_PACKAGES){

            $NUGET_FULL_NAME = $ANALYZER_PACKAGE.NugetFullname
            $NUGET_PATH = $ANALYZER_PACKAGE.NugetPath
            Write-Output "Using NuGet package: $NUGET_FULL_NAME"

            # Breaking down resulting diff into single diagnostics;
            # Checking pre-filled csv-file to filter out possible DIAGNOSTIC_IDs
            foreach ($ANALYZER_PACKAGE_DETAILS_ROW in $ANALYZER_PACKAGE_DETAILS){
            
                $ANALYZER_PACKAGE_NAME = $ANALYZER_PACKAGE_DETAILS_ROW.HostingPackageName
                $ANALYZER_ASSEMBLY = $ANALYZER_PACKAGE_DETAILS_ROW.AssemblyName
                $TYPE = $ANALYZER_PACKAGE_DETAILS_ROW.Type
                $DIAGNOSTIC_ID = $ANALYZER_PACKAGE_DETAILS_ROW.DiagnosticID

                if ($NUGET_FULL_NAME -ne $ANALYZER_PACKAGE_NAME ) {
                    continue
                }

                Write-Output "Using DIAGNOSTIC_ID: $DIAGNOSTIC_ID with TYPE: $TYPE"

                $OUTPUT_FILENAME="${REPO_NAME}__${SOLUTION_FILENAME}__${LAST_COMMIT}__${NUGET_FULL_NAME}__${DIAGNOSTIC_ID}"
                Write-Output "Creating OUTPUT_FILENAME: $OUTPUT_FILENAME"

                if ($TYPE -eq "DIAGNOSTIC_ANALYZER") {

                    $ANALYSIS_FILEPATH="./raw_dataset/analysis_files/${OUTPUT_FILENAME}.xml"
                    Write-Output "Creating ANALYSIS_FILEPATH: $ANALYSIS_FILEPATH"

                    Write-Output "
roslynator analyze $SOLUTION_FILEPATH \
-v quiet \
--output $ANALYSIS_FILEPATH \
--report-not-configurable \  # Mostly compiler diagnostics (CSxxxx)
--ignore-analyzer-references \   # Only use our own analyzer assemblies
--analyzer-assemblies $NUGET_PATH \
--supported-diagnostics $DIAGNOSTIC_ID `n"

                } else { # $TYPE -eq "CODEFIX_PROVIDER"

                    $DIFF_FILENAME="${OUTPUT_FILENAME}.diff"

                    Write-Output "Creating DIFF_FILENAME: $DIFF_FILENAME"

                    # This basically produces a diff
                    Write-Output "
roslynator fix $SOLUTION_FILEPATH \
--ignore-analyzer-references \
--analyzer-assemblies $NUGET_PATH \
--supported-diagnostics $DIAGNOSTIC_ID `n"

                    cd $REPO_TO_ANALYZE
                    $DIFF_CONTENT=$(git diff)

                    if ( "$DIFF_CONTENT" -eq "" ) {
                        Write-Output "Empty diff!"
                    } else {
                        $DIFF_FILEPATH = "$CURRENT_DIR/raw_dataset/diffs/$DIFF_FILENAME"
                        if (!(Test-Path $DIFF_FILEPATH)) {
                            [void](New-Item -ItemType "file" -Path $DIFF_FILEPATH)
                        }
                        $DIFF_CONTENT > $DIFF_FILEPATH
                        # git reset --hard
                    }

                    cd $CURRENT_DIR
                    
                }
                break
            }
            break
        }
        break
    }
    break
}
