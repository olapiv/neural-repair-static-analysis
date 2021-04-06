import json
import requests


def query_nuget_org():
    # Taking an unreasonable amount such as 5000, simply returns 20...
    params = {
        'q': 'analyzer',  # TODO: Consider also using "analysis"?
        'take': 800,
        'prerelease': 'false',
        # 'skip': 0,
        # 'semVerLevel': ''
        # 'packageType': ''
    }
    response = requests.get("https://azuresearch-usnc.nuget.org/query", params)
    responseDict = response.json()

    print("Number of packages retrieved: ", len(responseDict["data"]))
    
    return responseDict


def write_response_to_file(responseDict, filename='nuget_api_response.json'):
    with open(filename, 'w') as fout:
        json_dumps_str = json.dumps(responseDict, indent=4)
        print(json_dumps_str, file=fout)


def read_respoonse_from_file(filename='nuget_api_response.json'):
    with open(filename) as f:
        responseDict = json.load(f)
    return responseDict


def generate_nuget_txt_list(responseDict):
    """
    Extract relevant information from nuget_api_response.json,
    which is the REST API response from nuget.org.
    """

    nugetPackages = []
    for nugetPackage in responseDict["data"]:
        nugetPackages += [nugetPackage["id"]]

    with open('nuget_packages.txt', 'w') as f:
        for nugetPackage in nugetPackages:
            f.write(nugetPackage + "\n")


if __name__ == "__main__":
    responseDict = query_nuget_org()
    write_response_to_file(responseDict)
    generate_nuget_txt_list(responseDict)
