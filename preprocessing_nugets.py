import json
import pandas as pd


def generate_nuget_txt_list():
    """
    Extract relevant information from nuget_api_response.json,
    which is the REST API response from nuget.org.
    """
    with open('nuget_api_response.json') as f:
        responseDict = json.load(f)

    nugetPackages = []
    for nugetPackage in responseDict["data"]:
        nugetPackages += [nugetPackage["id"]]

    with open('nuget_packages.txt', 'w') as f:
        for nugetPackage in nugetPackages:
            f.write(nugetPackage + "\n")


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


def unique_source_packages(df, original_packages='nuget_packages.txt'):
    "All packages that have their own diagnostic ids, disregarding versioning"

    # Not optimal - any dots followed by numbers are removed
    df = df['HostingPackageName'].str.replace(r'\.\d+', '')
    df.drop_duplicates(inplace=True)
    with pd.option_context(
        'display.min_rows', 70,
        'display.max_rows', 70,
        'display.max_colwidth', 300
    ):
        print(df)


def missed_packages(df, original_packages='nuget_packages.txt'):
    """
    All packages that were not in the original list of NuGet analyzer packages, but
    have DiagnosticAnalyzers/CodeFixProviders and packages of the original list use
    them as dependencies.
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


def calculate_analyzer_statistics(csv_file="analyzer_package_details.csv"):

    df = pd.read_csv(csv_file)
    # TODO: Find out why duplicates exist
    df.drop_duplicates(inplace=True)
    total_das_cps(df)
    unique_diagnostic_ids(df)

    duplicate_diagnostic_ids(df)

    unique_source_packages(df)
    missed_packages(df)

    # TODO: Find
    # 1. Percentage of diagnostic_analyzers that have a codefix_provider


if __name__ == "__main__":
    calculate_analyzer_statistics()
