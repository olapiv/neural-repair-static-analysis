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

    TODO: Find out why this happens. Dependencies?
    TODO: Find out whether it's possible to save dependencies in a separate folder.
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


def calculate_analyzer_statistics(csv_file="analyzer_package_details.csv"):

    df = pd.read_csv(csv_file)
    # TODO: Find out why duplicates exist
    df.drop_duplicates(inplace=True)
    total_das_cps(df)
    unique_diagnostic_ids(df)

    duplicate_diagnostic_ids(df)

    # TODO: Find
    # 1. Percentage of diagnostic_analyzers that have a codefix_provider


if __name__ == "__main__":
    calculate_analyzer_statistics()
