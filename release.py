"""
Get the release information from a specific repository
curl 'https://api.github.com/repos/sosey/testbot/releases'
testbot.rel is example response for the sosey/testbot repo

# used to render the markdown to HTML which can be walked
# or used in the html page as-is
pip install mistune

# Use bs4 to walk the html tree for parsing
# from bs4 import BeautifulSoup as bs
# .stripped_strings on the bs4 object will remove the html tags
# bs(m, "html.parser")  # will return a bs object for parsing
"""
# SSLError: Can't connect to HTTPS URL because the SSL module is not available.
# using pycurl for now as an example
# import requests

import json
import mistune
import os
import pycurl
from io import BytesIO


def MakeSummaryPage(data=None, outpage=""):
    """Make a summary HTML page from a list of repos with release information.

    Data should be a list of dictionaries
    """

    if not isinstance(data, list):
        raise TypeError("Expected data to be a list of dictionaries")
    if not outpage:
        raise TypeError("Expected outpage name")

    # print them to a web page we can display for ourselves,
    print("Checking for older html file")
    if os.access(outpage, os.F_OK):
        os.remove(outpage)
    html = open(outpage, 'w')

    # this section includes the javascript code and google calls for the
    # interactive features (table sorting)

    b = '''
    <html>
      <head>  <title>Software Status Page </title>
       <meta charset="utf-8">
        <script type="text/javascript" src="https://www.google.com/jsapi"></script>
        <script type="text/javascript">
          google.load("visualization", "1", {packages:["table"]});
          google.setOnLoadCallback(drawTable);
          function drawTable() {
            var data = new google.visualization.DataTable();
            data.addColumn("string", "Software");
            data.addColumn("string", "Version");
            data.addColumn("string", "Repository Link");
            data.addColumn("string", "Reprocessing Information");
            data.addColumn("string", "Released");
            data.addColumn("string", "Author")
            data.addRows([
    '''
    html.write(b)

    for repo in data:
        # below is the google table code
        software = repo['name']
        version = repo['version']
        descrip = RenderHTML(repo['release_notes'])
        website = repo['website']
        date = repo['published']
        author = repo['author']
        avatar = repo['avatar']
        html.write("[\"{}\",\"{}\",\'<a href=\"{}\">{}</a>\',{}{}{},\"{}\",\'<a href=\"{}\">{}</a>\'],\n".format(software, version, website, "Code Repository", chr(96), descrip, chr(96), date, avatar, author))

    ee = '''  ]);
    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true});
    }
    </script>
    </head>
    <body>
    <br>Click on the column fields to sort
    <div id="table_div"></div>
    </body>
    </html>
    '''
    html.write(ee)
    html.close()


def RenderHTML(md=""):
    """Turn markdown string into beautiful soup structure."""
    if not md:
        return ValueError("Supply a string with markdown")
    m = mistune.markdown(md)
    return m


def GetReleaseSpecs(data=None):
    """parse out the release information from the json object.

    This assumes data release specified in data as a dictionary
    """
    if not isinstance(data, dict):
        raise TypeError("Wrong input data type, expected list")

    specs = {}
    try:
        specs['release_notes'] = data['body']
    except KeyError:
        specs['release_notes'] = "None available"
    try:
        specs['name'] = data['repo_name']
    except KeyError:
        try:
            specs['name'] = data['name']
        except KeyError:
            specs['name'] = "No Name Set"
    try:
        specs['version'] = data['tag_name']
    except KeyError:
        try:
            specs['version'] = data['name']
        except KeyError:
            specs['version'] = "No versions"
    try:
        specs['published'] = data['published_at']
    except KeyError:
        specs['published'] = "No Data"
    try:
        specs['website'] = data['html_url']
    except KeyError:
        specs['website'] = 'No website provided'
    try:
        specs['author'] = data['author']['login']
    except KeyError:
        specs['author'] = "STScI"
    try:
        specs['avatar'] = data['author']['avatar_url']
    except KeyError:
        specs['avatar'] = "None Provided"
    return specs


def ReadResponseFile(response=""):
    """Read a json response file."""
    if not response:
        raise ValueError("Please specify json file to read")
    with open(response, 'r') as f:
        data = json.load(f)
    return data


def GetAllReleases(org="", outpage=""):
    """Get the release information for all repositories in an organization.

    Returns a list of dictionaries with information on each repository
    The github api only returns the first 30 repos by default.
    At most it can return 100 repos at a time. Multiple calls
    need to be made for more.
    """

    if not org:
        raise ValueError("Please supply github organization")

    orgrepo_url = "https://api.github.com/orgs/{0:s}/repos?per_page=10".format(org)
    repos_url = "https://api.github.com/repos/{0:s}/".format(org)
    print("Examinging {0:s}....".format(orgrepo_url))
    # Get a list of the repositories
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, orgrepo_url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    res = buffer.getvalue().decode('iso-8859-1')
    results = json.loads(res)  # list of dicts
    repo_names = []
    print(repo_names)
    # no account for orgs without repos
    for i in range(0, len(results), 1):
        repo_names.append(results[i]['name'])

    # Loop through all the repositories to get release information
    # Repositories may have multiple releases
    repo_releases = []
    for name in repo_names:
        data = CheckForRelease(repos_url, name)  # returns a list of results
        # expand the release information into separate dicts
        for d in data:
            relspecs = GetReleaseSpecs(d)
            relspecs['repo_name'] = name
            repo_releases.append(relspecs)

    MakeSummaryPage(repo_releases, outpage=outpage)



def CheckForRelease(repos="", name=""):
    """Check for release information, not all repos may have releases.

    Repositories without release information may have tag information
    """
    rel_url = repos + ("{0:s}/releases".format(name))
    tags_url = repos + ("{0:s}/tags".format(name))
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, rel_url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    results = buffer.getvalue().decode('iso-8859-1')
    jdata = json.loads(results)
    if len(jdata) == 0:
        c = pycurl.Curl()
        buffer = BytesIO()
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.URL, tags_url)  # get info from tags
        c.perform()
        c.close()
        results = buffer.getvalue().decode('iso-8859-1')
        jdata = json.loads(results)
        for j in jdata:
            j['html_url'] = j['commit']['url']
            j['tag_name'] = j['name']
            j['name'] = name
    return jdata

# def GetAllReleases(user="", repo=""):
#     """Get all the release information for a specific repository.
#
#     This currently isn't working on my mac because
#     SSLError: Can't connect to HTTPS URL because the SSL
#     module is not available.
#     """
#
#     if not user:
#         raise ValueError("Please supply github user")
#     if not repo:
#         raise ValueError("Please supply a github repo name")
#
#     repo_url = "https://api.github.com/repos"
#     req = "/".join([repo_url, user, repo, "releases"])
#     return requests.get(req, verify=False).json()

# make a pycurl call for now becuase of the https issue
if __name__ == "__main__":

    """Create and example output from just the test repository."""

    url = "https://api.github.com/repos/sosey/testbot/releases"
    page = ReadResponseFile('testbot.rel')  # reads into a list of dicts
    specs = GetReleaseSpecs(page.pop())  # just send in the one dict
    specs['name'] = 'testbot'
    MakeSummaryPage([specs], 'testbot_release.html')
