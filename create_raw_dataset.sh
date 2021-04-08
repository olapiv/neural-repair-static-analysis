#!/bin/bash

CLONED_REPOS_DIR="./cloned_repos_to_analyze"
CURRENT_DIR=$PWD
LINE="HEADER"

while IFS=, read -r REPO_NAME REPO_URL; do

    if [ "$LINE" == "HEADER" ]; then
        LINE="BODY"
        continue
    fi

    REPO_TO_ANALYZE="${CLONED_REPOS_DIR}/${REPO_NAME}"

    echo "Cloning $REPO_NAME"
    git clone $REPO_URL $REPO_TO_ANALYZE

    cd $REPO_TO_ANALYZE
    LAST_COMMIT=$(git log -n 1 --pretty=format:"%H")
    echo "Last commit: $LAST_COMMIT"
    cd "$CURRENT_DIR"

    SOLUTION_FILEPATHS=()
    while IFS= read -r -d $'\0'; do
        SOLUTION_FILEPATHS+=("$REPLY")
    done < <(find $REPO_TO_ANALYZE -name "*.sln" -print0)
    echo "Available solution files: $SOLUTION_FILEPATHS"

    # Cannot apply roslynator by file; only by project/solution;
    # Might as well apply to entire solution.
    for SOLUTION_FILEPATH in "${SOLUTION_FILEPATHS[@]}"; do

        SOLUTION_FILE=${SOLUTION_FILEPATH##*/}

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

                echo "Using DIAGNOSTIC_ID: $DIAGNOSTIC_ID with TYPE: $TYPE"

                FILENAME="${REPO_NAME}__${SOLUTION_FILE}__${LAST_COMMIT}__${DIAGNOSTIC_ID}"

                echo "Creating FILENAME: $FILENAME"

                if [ "$TYPE" == "DIAGNOSTIC_ANALYZER" ]; then

                    ANALYSIS_FILENAME="./analysis_files/${FILENAME}.xml"

                    echo "Creating ANALYSIS_FILENAME: $ANALYSIS_FILENAME"

                    echo -e "\n
roslynator analyze $SOLUTION_FILEPATH \
-v quiet \
--output $ANALYSIS_FILENAME \
--report-not-configurable \  # Mostly compiler diagnostics (CSxxxx)
--ignore-analyzer-references \   # Only use our own analyzer assemblies
--analyzer-assemblies $ANALYZER_PACKAGE \
--supported-diagnostics $DIAGNOSTIC_ID \n"

                else # $TYPE == "CODEFIX_PROVIDER"

                    DIFF_FILENAME="./diffs/${FILENAME}.diff"

                    echo "Creating DIFF_FILENAME: $DIFF_FILENAME"

                    # This basically produces a diff
                    echo -e "\n
roslynator fix $SOLUTION_FILEPATH \
--ignore-analyzer-references \
--analyzer-assemblies $ANALYZER_PACKAGE \
--supported-diagnostics $DIAGNOSTIC_ID \n"

                    touch $DIFF_FILENAME

                    git diff -p ${REPO_TO_ANALYZE} >$DIFF_FILENAME

                    cd $REPO_TO_ANALYZE
                    git reset --hard
                    cd "$CURRENT_DIR"

                fi

            done <analyzer_package_details_filtered.csv

        done
    done

done <github_repos.csv
