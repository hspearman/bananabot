import json
import random
import praw
import sys
import time
from praw.errors import ClientException, APIException
from requests.packages.urllib3.exceptions import HTTPError

# Constants
DELIMITER = " "
SUBREDDIT = "all"
LIMIT_PER_REQUEST = 100
KEYWORDS = []
USER_AGENT = USERNAME = PASSWORD = TEMPLATE = ''
TIME_TO_SLEEP = 60
RESOURCES_DIRECTORY = 'Resources'
FILE_PATH_TEMPLATE = "./{0}/{1}"


def main():
    # Init connection to reddit API
    load_config_data()
    praw_handle = praw.Reddit(user_agent=USER_AGENT)
    praw_handle.login(USERNAME, PASSWORD)

    # TODO: Improve error reporting
    # Continually parse comments
    replied_list = get_resources_json_file("replied_list.json")
    black_list_subreddits = get_black_list_subreddits()
    while True:
        try:
            parse_comments(praw_handle, black_list_subreddits, replied_list)
        except HTTPError:
            time.sleep(60)
        except ClientException as e:
            print("Encountered client-side error!")
            time.sleep(60)
        except APIException as e:
            print("Encountered server-side error!")
            time.sleep(60)


def parse_comments(praw_handle, black_list_subreddits, replied_list):
    while True:
        # Iterate through comments
        all_comments = praw_handle.get_comments(SUBREDDIT)
        for comment in all_comments:

            # Calculate criteria for match
            is_self = comment.author is USERNAME
            is_black_listed = comment.subreddit.display_name in black_list_subreddits
            any_keyword_found = contains_any_keyword(KEYWORDS, comment.body.lower())
            already_replied = comment.id in replied_list

            # If comment is match, respond
            is_match = any_keyword_found and \
                       not is_black_listed and \
                       not is_self and \
                       not already_replied
            if is_match:
                # Respond with generated comment
                reply = generate_comment()
                comment.upvote()
                comment.reply(reply)
                print(reply)


def generate_comment():
    # Deserialize JSON data from files
    openers = get_resources_json_file("openers.json")
    transitions = get_resources_json_file("transitions.json")
    content = get_resources_json_file("contents.json")

    # TODO: Handle via exception
    # If any data is missing, terminate program
    if not openers or \
        not transitions or \
        not content:
        print("Failed to obtain content generation resources!")
        sys.exit()

    # Generate content via template
    return TEMPLATE.format(
            random.choice(openers),
            random.choice(transitions),
            random.choice(content)
    )


def get_resources_json_file(filename):
    data = get_data_from_file(FILE_PATH_TEMPLATE.format(RESOURCES_DIRECTORY, filename))
    try:
        return json.loads(data)
    except ValueError:
        print("Failed to decode JSON!")
        sys.exit()


def get_data_from_file(path):
    try:
        with open(path, encoding='utf-8') as data_file:
            return data_file.read()
    except (IOError, FileNotFoundError) as e:
        print("Failed to open file!")
        sys.exit()


def get_black_list_subreddits():
    # Deserialize JSON data from files
    black_list_subs = get_resources_json_file("black_list.json")
    botiquette_black_list_subs = get_resources_json_file("botiquette_black_list.json")

    # Combine sub-lists into one list
    botiquette_black_listed_subs = \
        botiquette_black_list_subs["posts-only"] + \
        botiquette_black_list_subs["disallowed"] + \
        botiquette_black_list_subs["permission"]

    # Get unique black list subreddits (via set theory logic)
    unique_black_listed_subs = list(set(black_list_subs) | set(botiquette_black_listed_subs))
    return unique_black_listed_subs


def load_config_data():
    config = get_resources_json_file("config.json")
    try:
        global USER_AGENT, USERNAME, PASSWORD, TEMPLATE, KEYWORDS
        USER_AGENT = config["useragent"]
        USERNAME = config["username"]
        PASSWORD = config["password"]
        TEMPLATE = config["template"]
        KEYWORDS = config["keywords"]
    except KeyError:
        print("Failed to load config!")


def contains_any_keyword(keywords, target):
    for keyword in keywords:
        if keyword in target:
            return True


main()
