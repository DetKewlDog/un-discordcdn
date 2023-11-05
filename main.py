import requests
from os import path, mkdir, walk


NO_MATCHES_FOUND = 9999999


def extract_url_from_text(text: str) -> tuple[str, int, int] | None:
    """
    function to extract a URL and its start/end index from a string
    input: text to extract the URL from
    output: extracted URL, start index of URL, end index of URL
    """

    # finds the index of 'h' from https://cdn.discordapp.com inside the given string
    start_index: int = text.find('https://cdn.discordapp.com')

    # no URL was found inside the string
    if start_index == -1:
        return

    # get the character that comes before the URL (could be quotation marks, space, etc)
    first_char: str = text[start_index - 1]

    # we only want a non alpha-numeric character, e.g. space, quotation marks, etc.
    if first_char.isalnum():
        return

    # we look for the character that appeared at the beginning of the URL
    # a space can split the URL in half, and overrides the index of the closing character
    # a closing parentheses can appear in markdown
    end_index: int = text.find(first_char, start_index)
    space_index: int = text.find(' ', start_index)
    paran_index: int = text.find(')', start_index)

    if end_index == -1: end_index = NO_MATCHES_FOUND
    if space_index == -1: space_index = NO_MATCHES_FOUND
    if paran_index == -1: paran_index = NO_MATCHES_FOUND

    end_index = min(min(end_index, space_index), paran_index)

    # if no results were found, then the link continues until the end of the string
    if end_index == NO_MATCHES_FOUND or end_index == -1:
        end_index = len(text) - 1

    return text[start_index:end_index], start_index, end_index


def get_file_name_from_url(url: str) -> str | None:
    """
    function extracts the name of a file from its URL
    input: the file's URL
    output: the name of the file
    """

    # removes the trailing / from a url
    # e.g. https://www.abc.com/ -> https://www.abc.com
    if url.endswith('/'):
        url = url[:-1]

    url = url.replace('https://', '')

    # splits the name of the file from the rest of the URL
    # www.abc.com/test.png -> test.png
    index: int = url.rfind('/') + 1

    # there was no file at the end of the URL
    if index == 0:
        return None

    file_name = url[index:]

    if file_name.endswith('?'):
        file_name = file_name[:-1]

    return file_name


def save_file_from_url(file_path: str, url: str) -> None:
    """
    function gets a file from a URL and saves it in a specified path
    input: the path where the file will be saved, the file's URL
    output: none
    """

    response = requests.get(url, allow_redirects=True)
    open(file_path, 'wb').write(response.content)


def update_file_url(text: str, file_name: str, start_index: int, end_index: int) -> str:
    """
    function replaces the URL that's inside a string with a
    path to a file with a name inside the /public directory
    input: the text to modify, the name of the file to serve as a replacement,
    the start and end indexes for the position of the URL string inside the target string
    output: the updated URL
    """

    new_url = '/' + file_name
    new_text = text[:start_index] + new_url + text[end_index:]
    return new_text


def update_url_in_line(line: str, project_path: str, include_public_dir: bool) -> str:
    """
    function saves a file that is inside a string (as a URL), and replaces that URL with the file's new path
    input: the line to modify, the path of the current working project directory, bool if to add /public/ to the new path
    output: returns the updated line, and saves the file from the URL inside the line to project_path/public/
    """

    extracted_url = extract_url_from_text(line)

    if extracted_url == None:
        return line

    url, start_index, end_index = extracted_url

    file_name = get_file_name_from_url(url)

    if file_name == None:
        return line

    public_dir = project_path + '/public'
    if not path.isdir(public_dir):
        mkdir(public_dir)

    file_path = public_dir + '/' + file_name
    save_file_from_url(file_path, url)

    if include_public_dir:
        file_name = 'public/' + file_name

    updated_line = update_file_url(line, file_name, start_index, end_index)
    return updated_line


def update_urls_in_file(file_path: str, project_path: str, include_public_dir: bool) -> None:
    """
    function replaces all Discord CDN URL's in a file with local directories,
    and saves the files located at said URLS to said directories (to the /public folder)
    input: the path of the file to modify, the root path of the project, bool if to add /public/ to the new path
    output: returns none, updates the file's content,
    creates a /public folder at project_path if didn't exist, and saves files there
    """
    try:
        with open(file_path, 'r', encoding='utf8') as file:
            lines: list = file.readlines()
    except UnicodeDecodeError as e:
        return

    old_lines = lines
    lines = [update_url_in_line(line, project_path, include_public_dir) for line in lines]

    # no changes have been made, so we don't need to write to this file
    if old_lines == lines: return

    # prints the amount of differences that have been made to the console
    diff = len(set(lines) - set(old_lines))
    print('{: <80}{: >20}'.format(file_path, f'{diff} Discord CDN URLs'))

    with open(file_path, 'w', encoding='utf8') as file:
        file.writelines(lines)


def update_urls_in_project(project_path: str) -> None:
    """
    function replaces all Discord CDN URL's in every file in a directory with local directories,
    and saves the files located at said URLS to said directories (to the /public folder)
    folders such as .git, node_modules and __pycache__ will not be modified
    input: the root path of the project
    output: returns none, updates the project files' content,
    creates a /public folder at project_path if didn't exist, and saves files there
    """
    ignored_dirs = { '.git', 'node_modules', '__pycache__' }

    for root, dirs, files in walk(project_path):
        for file in files:
            file_path: str = path.join(root, file)

            # exclude directories that include one of the ignored directories
            if True in [dir in file_path for dir in ignored_dirs]: continue

            # if the file we're modifying is a markdown file, then we should include /public/ to the new paths (TODO: check if necessary)
            update_urls_in_file(file_path, project_path, file_path.endswith('.md'))


update_urls_in_project(r'E:\Projects\portfolio-site')