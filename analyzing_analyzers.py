import pandas as pd
import json


def total_das_cps(df):
    """
    Total diagnostic_analyzers & codefix_providers
    """
    print("Total rows")
    diagnostic_analyzers = df[df['Type'].str.match('DIAGNOSTIC_ANALYZER')]
    codefix_providers = df[df['Type'].str.match('CODEFIX_PROVIDER')]
    num_da = len(diagnostic_analyzers.index)
    num_cp = len(codefix_providers.index)
    print("da: ", num_da)
    print("cp: ", num_cp)


def unique_diagnostic_ids(df):
    print("Unique diagnostic ids")
    diagnostic_analyzers = df[df['Type'].str.match('DIAGNOSTIC_ANALYZER')]
    codefix_providers = df[df['Type'].str.match('CODEFIX_PROVIDER')]
    num_da = diagnostic_analyzers['DiagnosticID'].nunique()
    num_cp = codefix_providers['DiagnosticID'].nunique()
    print("da: ", num_da)
    print("cp: ", num_cp)


def duplicate_diagnostic_ids(df):
    """
    Seems to happen mostly because the same packages are downloaded multiple times, 
    but with different versions. Specifically:
    StyleCop:
        1. StyleCop.Analyzers.1.1.118
        2. StyleCop.Analyzers.Unstable.1.2.0.333
        3. StyleCop.Analyzers.1.0.0
        4. StyleCop.Analyzers.1.0.2
    XUnit:
        1. xunit.analyzers.0.10.0
        2. xunit.analyzers.0.7.0
    SonarAnalyzer.CSharp:
        1. SonarAnalyzer.CSharp.8.20.0.28934
        2. SonarAnalyzer.CSharp.1.21.0
        3. SonarAnalyzer.CSharp.1.23.0.1857
        4. SonarAnalyzer.CSharp.8.6.0.16497
        5. SonarAnalyzer.CSharp.8.7.0.17535

    This is because a number of analyzer packages use other analyzer packages
    as dependencies. Sometimes they simply bundle different analyzer packages
    without creating any DiagnosticAnalyzers / CodeFixProviders themselves.
    The downside of this, is that they often reference outdated versions. This
    is why we can see so many different versions of the same packages.
    """
    print("Duplicate diagnostic ids")
    diagnostic_analyzers = df[df['Type'].str.match('DIAGNOSTIC_ANALYZER')]
    codefix_providers = df[df['Type'].str.match('CODEFIX_PROVIDER')]
    da_duplicates = pd.concat(
        g for _, g in diagnostic_analyzers.groupby("DiagnosticID") if len(g) > 1)
    cp_duplicates = pd.concat(
        g for _, g in codefix_providers.groupby("DiagnosticID") if len(g) > 1)

    with pd.option_context(
        'display.min_rows', 50,
        'display.max_rows', 50
    ):
        print(da_duplicates)
        print(cp_duplicates)


def unique_source_packages(df, print_bool=True):
    """All packages that have their own diagnostic ids, whereby packages
    with multiple versions are only counted once."""

    # Not optimal - any dots followed by numbers are removed
    df_hosting_packages = df['HostingPackageName'].str.replace(r'\.\d+', '')
    df_hosting_packages.drop_duplicates(inplace=True)
    if print_bool:
        with pd.option_context(
            'display.min_rows', 70,
            'display.max_rows', 70,
            'display.max_colwidth', 300
        ):
            print(df)
    return df_hosting_packages


def missed_packages(df, original_packages='nuget_packages.txt'):
    """
    All packages that were not in the original list of NuGet analyzer packages, but
    have DiagnosticAnalyzers/CodeFixProviders and packages of the original list use
    them as dependencies.

    This means we are using their diagnostics for the dataset, but they are potentially
    outdated versions.

    Queried for nuget.org for "analyzers"
    Problem:
    --> Did not query for "analyzer" e.g. 
          Microsoft.AnalyzerPowerPack
          SmartAnalyzers.ExceptionAnalyzer
          TODO: Redo search with "analyzer"
    --> Also missed "Microsoft.CodeAnalysis.CSharp"
    --> System packages may not be on NuGet.org e.g.
          System.Runtime.Analyzers
          System.Runtime.InteropServices.Analyzers
    """
    print("Missed packages")

    # Not optimal - any dots followed by numbers are removed
    df = df['HostingPackageName'].str.replace(r'\.\d+', '')
    df.drop_duplicates(inplace=True)

    original_packages_list = [line.strip() for line in open(original_packages)]
    df_missed_packages = df[~df.isin(original_packages_list)]

    with pd.option_context(
        'display.min_rows', 100,
        'display.max_rows', 100,
        'display.max_colwidth', 300
    ):
        print(df_missed_packages)


def is_hosting(package_name, dependency_dict, source_packages, depth=1):
    package_name_id = package_name.split("__")[0]
    # print(f"{' '*depth}package_name_id: {package_name_id}")
    if package_name_id in source_packages:
        # print(f"{' '*depth}>>>>>>SOURCE!<<<<<<")
        return True

    # print(f"{' '*depth}Not a source")

    filtered_dep = dependency_dict[package_name]
    # print(f"{' '*depth}filtered_dep: {filtered_dep}")

    for package, _ in filtered_dep.items():

        # Go deeper
        if is_hosting(package, filtered_dep, source_packages, depth + 3):
            return True

    # print(f"{' '*depth}Not hosting packages")
    return False


def pure_host_packages(df, original_packages='nuget_packages.txt', dependency_json='nuget_deps.json', print_bool=True):
    """
    Packages that only host other analyzers without providing own analyzers.
    They can therefore also be installed as analyzers.
    """
    print("Calculating pure host NuGet packages")

    source_packages = unique_source_packages(df, print_bool=False).to_list()
    with open(original_packages) as f:
        nuget_packages = [x.rstrip() for x in f]  # remove line breaks

    # Could also be hosting nothing:
    potential_host_packages = list(set(nuget_packages) - set(source_packages))
    # --> e.g. [Apex.Analyzers.Immutable.Semantics, Thor.Analyzer.Legacy, CESCodeAnalyzerTest]

    with open(dependency_json) as json_file:
        dependency_structure = json.load(json_file)

    all_versioned_packages = dependency_structure.keys()
    # --> e.g. [Apex.Analyzers.Immutable.Semantics__1.1, Thor.Analyzer.Legacy__3.2, CESCodeAnalyzerTest__1.0]

    potential_host_packages_versioned = []
    for host_package in potential_host_packages:
        for versioned_package in all_versioned_packages:
            versioned_package_id = versioned_package.split("__")[0]
            if host_package == versioned_package_id:
                potential_host_packages_versioned.append(versioned_package)

    host_packages = [package for package in potential_host_packages_versioned if is_hosting(
        package, dependency_structure, source_packages)]

    if print_bool:
        for package in host_packages:
            print(package)
        print("Number host_packages: ", len(host_packages))

    return host_packages


def useless_packages(df, original_packages='nuget_packages.txt', print_bool=True):
    """
    Packages that neither host other analyzers nor provide own analyzers;
    Practically irrelevant packages.
    """
    print("Calculating useless NuGet packages - neither host not source.")

    with open(original_packages) as f:
        nuget_packages = [x.rstrip() for x in f]

    source_packages = unique_source_packages(df, print_bool=False).to_list()
    host_packages = pure_host_packages(df, print_bool=False)

    useless_packages = list(set(nuget_packages) -
                            set(source_packages) - set(host_packages))

    if print_bool:
        for package in useless_packages:
            print(package)
        print("Number useless_packages: ", len(useless_packages))

    return useless_packages


def is_referencing(package_name, dependency_dict, source_package, depth=1):
    package_name_id = package_name.split("__")[0]
    # print(f"{' '*depth}package_name_id: {package_name_id}")
    if package_name_id == source_package:
        # print(f"{' '*depth}>>>>>>REFERENCING!<<<<<<")
        return True

    # print(f"{' '*depth}Not referencing")

    filtered_dep = dependency_dict[package_name]
    # print(f"{' '*depth}filtered_dep: {filtered_dep}")

    for package, _ in filtered_dep.items():

        # Go deeper
        if is_referencing(package, filtered_dep, source_package, depth + 3):
            return True

    # print(f"{' '*depth}Not referencing package")
    return False


def most_referenced_source_packages(df, dependency_json='nuget_deps.json', print_bool=True):
    """
    Counting the number of times each analyzer package has been referenced in other
    NuGet packages.
    """
    print("Calculating most referenced source packages")
    
    source_packages = unique_source_packages(df, print_bool=False).to_list()
    with open(dependency_json) as json_file:
        dependency_structure = json.load(json_file)

    all_versioned_packages = dependency_structure.keys()
    source_packages_ref_counts = {}

    for source_package in source_packages:
        source_packages_ref_counts[source_package] = 0
        for versioned_package in all_versioned_packages:
            versioned_package_id = versioned_package.split("__")[0]
            if source_package == versioned_package_id:
                continue
            if is_referencing(versioned_package, dependency_structure, source_package):
                source_packages_ref_counts[source_package] += 1

    relevant_packages = {k: v for k,
                         v in source_packages_ref_counts.items() if v > 0}

    if print_bool:
        print(json.dumps(relevant_packages, indent=2))
        print("Number referenced_packages: ", len(relevant_packages.keys()))

    return relevant_packages


def calculate_analyzer_statistics(csv_file="analyzer_package_details.csv"):

    df = pd.read_csv(csv_file)
    # TODO: Find out why duplicates exist
    # df.drop_duplicates(inplace=True)
    # total_das_cps(df)
    # unique_diagnostic_ids(df)

    # duplicate_diagnostic_ids(df)

    # unique_source_packages(df)
    # missed_packages(df)
    # pure_host_packages(df)
    # useless_packages(df)
    most_referenced_source_packages(df)


if __name__ == "__main__":
    calculate_analyzer_statistics()
