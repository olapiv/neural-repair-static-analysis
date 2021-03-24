#!/bin/bash

while read GH_REPO_URL do

    git clone GH_REPO_URL github_repo_to_fix/

    LAST_COMMIT=$(git log -n 1 --pretty=format:"%H")

    declare -a SOLUTION_FILES=("file1.sltn" "file2.sltn" "file.sltn")
    # TODO: Search for all .sltn files

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    for SOLUTION_FILE in "${SOLUTION_FILES[@]}" do

        for ASSEMBLY_DLL in /analyzer_assemblies/*.dll; do

            # Breaking down resulting diff into single diagnostics; 
            # Checking pre-filled csv-file to filter out possible DIAGNOSTIC_IDs
            while IFS=, read -r col1 col2 ASSEMBLY_DLL_CSV DIAGNOSTIC_ID do

                if [ "$ASSEMBLY_DLL" != "$ASSEMBLY_DLL_CSV" ]; then
                    continue
                fi

                FILENAME = $SOLUTION_FILE + "__" + $LAST_COMMIT + "__" + $DIAGNOSTIC_ID
                ANALYSIS_FILEPATH = "/analysis_files/" + $FILENAME + ".xml"
                DIFF_FILEPATH = "/diffs/" + $FILENAME + ".diff"

                roslynator analyze SOLUTION_FILE \
                    -v quiet \
                    --output $ANALYSIS_FILEPATH \
                    --report-not-configurable \  # Mostly compiler diagnostics (CSxxxx)
                    --ignore-analyzer-references \  # Only use our own analyzer assemblies 
                    --analyzer-assemblies ASSEMBLY_DLL \
                    --supported-diagnostics $DIAGNOSTIC_ID

                # This basically produces a diff
                roslynator fix SOLUTION_FILE 
                    --ignore-analyzer-references \
                    --analyzer-assemblies ASSEMBLY_DLL \
                    --supported-diagnostics $DIAGNOSTIC_ID

                git diff > $DIFF_FILENAME
                git reset --hard

            done < assembly_breakdown.csv

        done
    done

done < github_repos.txt
