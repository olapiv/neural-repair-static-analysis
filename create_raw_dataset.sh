#!/bin/bash

while read GH_REPO_URL do

    git clone GH_REPO_URL github_repo_to_fix/

    LAST_COMMIT=$(git log -n 1 --pretty=format:"%H")

    declare -a SOLUTION_FILES=("file1.sltn" "file2.sltn" "file.sltn")
    # TODO: Search for all .sltn files

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    for SOLUTION_FILE in "${SOLUTION_FILES[@]}" do

        for ANALYZER_PACKAGE in /nuget_analyzer_packages/; do

            # Breaking down resulting diff into single diagnostics; 
            # Checking pre-filled csv-file to filter out possible DIAGNOSTIC_IDs
            while IFS=, read -r col1 col2 ANALYZER_PACKAGE_CSV ANALYZER_ASSEMBLY TYPE DIAGNOSTIC_ID do

                if [ "$ANALYZER_PACKAGE" != "$ANALYZER_PACKAGE_CSV" ]; then
                    continue
                fi

                FILENAME = $SOLUTION_FILE + "__" + $LAST_COMMIT + "__" + $DIAGNOSTIC_ID

                if [ "$TYPE" == "DIAGNOSTIC_ANALYZER" ]; then

                    ANALYSIS_FILENAME = "/analysis_files/" + $FILENAME + ".xml"

                    roslynator analyze SOLUTION_FILE \
                        -v quiet \
                        --output $ANALYSIS_FILENAME \
                        --report-not-configurable \  # Mostly compiler diagnostics (CSxxxx)
                        --ignore-analyzer-references \  # Only use our own analyzer assemblies 
                        --analyzer-assemblies $ANALYZER_PACKAGE \
                        --supported-diagnostics $DIAGNOSTIC_ID
                    
                else  # $TYPE == "CODEFIX_PROVIDER"

                    DIFF_FILENAME = "/diffs/" + $FILENAME + ".diff"

                    # This basically produces a diff
                    roslynator fix SOLUTION_FILE 
                        --ignore-analyzer-references \
                        --analyzer-assemblies $ANALYZER_PACKAGE \
                        --supported-diagnostics $DIAGNOSTIC_ID

                    git diff > $DIFF_FILENAME
                    git reset --hard

                fi

            done < analyzer_package_details.csv

        done
    done

done < github_repos.txt
