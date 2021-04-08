#!/bin/bash

REPO_TO_FIX_DIR="github_repo_to_fix"

while IFS=, read -r REPO_NAME REPO_URL; do

    echo "Cloning $REPO_NAME"
    git clone $REPO_URL $REPO_TO_FIX_DIR

    # TODO: Make sure this not happening in our repo....:
    LAST_COMMIT=$(git log -n 1 --pretty=format:"%H")
    echo "Last commit: $LAST_COMMIT"

    SOLUTION_FILES=()
    while IFS= read -r -d $'\0'; do
        SOLUTION_FILES+=("$REPLY")
    done < <(find $REPO_TO_FIX_DIR -name "*.sln" -print0)
    echo "Available solution files: $SOLUTION_FILES"

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    for SOLUTION_FILE in "${SOLUTION_FILES[@]}"; do

        echo "Working with SOLUTION_FILE: $SOLUTION_FILE"

        for ANALYZER_PACKAGE in nuget_analyzer_packages/*/; do

            PREFIX="nuget_analyzer_packages/"
            SUFIIX="/"
            ANALYZER_PACKAGE=${ANALYZER_PACKAGE#"$PREFIX"}
            ANALYZER_PACKAGE=${ANALYZER_PACKAGE%"$SUFIIX"}
            echo "Using NuGet package: $ANALYZER_PACKAGE"

            # Breaking down resulting diff into single diagnostics;
            # Checking pre-filled csv-file to filter out possible DIAGNOSTIC_IDs
            while IFS=, read -r ANALYZER_PACKAGE_CSV ANALYZER_ASSEMBLY TYPE DIAGNOSTIC_ID; do

                if [ "$ANALYZER_PACKAGE" != "$ANALYZER_PACKAGE_CSV" ]; then
                    continue
                fi

                FILENAME="${SOLUTION_FILE}__${LAST_COMMIT}__${DIAGNOSTIC_ID}"
                echo "Creating FILENAME: $FILENAME"

                if [ "$TYPE" == "DIAGNOSTIC_ANALYZER" ]; then

                    ANALYSIS_FILENAME="/analysis_files/${FILENAME}.xml"
                    echo "Creating ANALYSIS_FILENAME: $ANALYSIS_FILENAME"

                    echo "roslynator analyze SOLUTION_FILE \
                        -v quiet \
                        --output $ANALYSIS_FILENAME \
                        --report-not-configurable \  # Mostly compiler diagnostics (CSxxxx)
                    --ignore-analyzer-references \   # Only use our own analyzer assemblies
                    --analyzer-assemblies $ANALYZER_PACKAGE \
                        --supported-diagnostics $DIAGNOSTIC_ID"

                else # $TYPE == "CODEFIX_PROVIDER"

                    DIFF_FILENAME="/diffs/${FILENAME}.diff"
                    echo "Creating DIFF_FILENAME: $DIFF_FILENAME"

                    # This basically produces a diff
                    echo "roslynator fix SOLUTION_FILE \
                        --ignore-analyzer-references \
                        --analyzer-assemblies $ANALYZER_PACKAGE \
                        --supported-diagnostics $DIAGNOSTIC_ID"

                    git diff >$DIFF_FILENAME

                    # TODO: Make sure this not happening in our repo....:
                    # git reset --hard

                fi

            done <analyzer_package_details.csv

        done
    done

done <github_repos.csv
