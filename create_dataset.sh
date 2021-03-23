#!/bin/bash

while read GH_REPO_URL do

    git clone GH_REPO_URL github_repo_to_fix/

    # TODO: Get latest commit
    LAST_COMMIT = ""

    declare -a SOLUTION_FILES=("file1.sltn" "file2.sltn" "file.sltn")
    # TODO: Search for all .sltn files

    for SOLUTION_FILE in "${SOLUTION_FILES[@]}" do
        for ASSEMBLY_DLL in /analyzer_assemblies/*.dll; do

            while IFS=, read -r col1 col2 DIAGNOSTIC_ID do

                # TODO: Check if row in assembly_breakdown is from ASSEMBLY_DLL; else continue

                # TODO: Check exact Roslynator flags again; Specifically:
                #   --ignore-compiler-errors

                roslynator fix SOLUTION_FILE --ignore-analyzer-references --analyzer-assemblies ASSEMBLY_DLL --supported-diagnostics $DIAGNOSTIC_ID
                # Problem: This produces a diff
                # --> We do not know which diagnostic instance prooduced which codefix

                DIFF_FILENAME = $SOLUTION_FILE + "__" + $LAST_COMMIT + "__" + $DIAGNOSTIC_ID + ".diff"
                git diff > $DIFF_FILENAME

                git reset --hard

            done < assembly_breakdown.csv

        done
    done

done < github_repos.txt
