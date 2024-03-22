import json

import pandas as pd

from tqdm import tqdm
import requests
import time
import os
from typing import Dict

def expand_factors(df: pd.DataFrame, columns: list) -> list:
    """
    Helper method to easily include factors from experiments
    Looks for magic value `$FACTORS$` to expand into experiment factors.
    For now, it aggregates over all experiments for all factors and unionizes them.

    **Example**: Assume that `df` contains a column called `factor_columns`
                    containing the factor column names [exp_factor_1, exp_factor_2]

    The following effects will happen, depending on what is contained in `columns`:
    columns: `[ col_1, col_2, $FACTORS$, col_3] -->
            [ col_1, col_2, exp_factor_1, exp_factor_2, col_3]` ($FACTORS$ is replaced)
    columns: `[ col_1, col_2, col_3] -->
            [ col_1, col_2, col_3]` (no effect as $FACTORS$ did not exist in the list)

    :param df: etl data
    :param columns: user-provided list of columns.
    :return: list with factor columns
    """
    MAGIC_KEY = "$FACTORS$"
    if MAGIC_KEY not in columns:
        return columns

    # look through dataframe and take union of all factor columns
    # (Note: across _all_ experiments in df)
    elements = df["factor_columns"].tolist()
    flat_list = [item for sublist in elements for item in sublist]
    factors = list(set.union(set(flat_list)))

    # replace in original list at same position
    i = columns.index(
        MAGIC_KEY
    )  # This raises ValueError if there's no 'b' in the list.
    columns[i: i + 1] = factors

    # check we do not have duplicates
    assert len(columns) == len(set(columns)), (
        f"{columns} contains duplicate values!\n"
        f"If $FACTORS$ was provided as a column value, "
        f"one of the other values is also contained in $FACTORS$!"
    )

    return columns


def convert_group_name_to_str(name):
    if type(name) == str:
        return name
    elif type(name) == int or type(name) == bool:
        return str(name)
    else:
        return "_".join([f"{n}" for n in name])


def print_etl_pipeline(etl_pipeline, name):

    extractors = "  ".join(etl_pipeline["extractors"].keys())
    extractors = f"| {extractors} |"
    extractors_divider = "-" * len(extractors)

    transformers = []
    lengths = []
    for step in etl_pipeline["transformers"]:
        transformers += ["|", "V"]
        if "name" in step:
            transformers.append(step["name"])
        else:
            assert len(step) == 1
            transformers.append(next(iter(step)))
        lengths.append(len(transformers[-1]))
    transformers += ["|", "V"]

    loaders = "  ".join(etl_pipeline["loaders"].keys())
    loaders = f"| {loaders} |"
    loaders_divider = "-" * len(loaders)

    max_length = max(lengths + [len(extractors), len(loaders)])
    extractors_divider = extractors_divider.center(max_length, " ")
    out = [
        extractors_divider,
        extractors.center(max_length, " ") + " Extractors",
        extractors_divider,
    ]

    for i, line in enumerate(transformers):
        line = line.center(max_length, " ")

        if i == 0:
            line = line + " Transformers"

        out.append(line)

    loaders_divider = loaders_divider.center(max_length, " ")
    out += [
        loaders_divider,
        loaders.center(max_length, " ") + " Loaders",
        loaders_divider,
    ]

    print(f"ETL Pipeline: {name}")
    for line in out:
        print(line)
    print()

def escape_tuple_str(tup) -> str:
    # check if tup is instance or iterable
    if not hasattr(tup, "__iter__"):
        return str(tup)
    as_str = "_".join(tup)
    # remove any dots
    as_str = as_str.replace(".", "")
    return as_str

def escape_dict_str(d: Dict) -> str:

    as_str = "_".join(f"{k.strip()}={v.strip()} " for k, v in d.items())

    # remove any dots
    as_str = as_str.replace(".", "")
    as_str = as_str.replace(" ", "")
    return as_str

def save_notion(filenames, etl_info, notion_dict):
    etl_output_dir = etl_info["etl_output_dir"]
    pipeline = etl_info["pipeline"]
    super_etl_name = etl_info["suite"]

    project = notion_dict["project"]
    parent_block_id = notion_dict["block_id"]

    s3_urls = save_files_to_s3("doe-suite-plots", project, super_etl_name, pipeline, etl_output_dir, filenames)

    # Your Notion API key
    notion_api_key = os.environ["NOTION_API_KEY"]

    url = f"https://api.notion.com/v1/blocks/{parent_block_id}/children"

    # Headers
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # update if newer version is available
    }

    clear_children = True
    if clear_children:
        notion_remove_children(url, headers)

    for plot_url in tqdm(s3_urls, desc="Adding images to Notion"):
        # URL to Notion API

        # Request body
        data = {
            "children": [
                {
                    "object": "block",
                    "type": "embed",
                    "embed": {
                        "url": plot_url
                    }
                }
            ]
        }
        # Convert Python dictionary to JSON
        data_json = json.dumps(data)

        # Send POST request to Notion API
        response = requests.patch(url, headers=headers, data=data_json)

        # Check the response
        if response.status_code != 200:
            print(f"Failed to add image, status code: {response.status_code}, for url {url}")
            print(f"Response: {response.text}")

def notion_remove_children(url, headers):
    # Send GET request to Notion API to retrieve child blocks
    response = requests.get(url, headers=headers)

    # Check the response
    if response.status_code == 200:
        # Convert the response to JSON
        children = response.json()

        # Iterate over each child block and delete it
        for child in children['results']:
            child_id = child['id']

            # URL to Notion API for deleting a block
            delete_url = f"https://api.notion.com/v1/blocks/{child_id}"

            # Send DELETE request to Notion API to delete the child block
            delete_response = requests.delete(delete_url, headers=headers)

            # Check the delete response
            if delete_response.status_code != 200:
                print(f"Failed to delete block with ID {child_id}, status code: {delete_response.status_code}")
                print(f"Response: {delete_response.text}")

            # Wait for 0.1 second to prevent rate limit
            time.sleep(0.1)

        print("Successfully deleted all existing plots")


def save_files_to_s3(bucket, project, super_etl_name, pipeline, local_output_dir, filenames, file_format="png", bucket_region="eu-central-1"):
    import boto3
    from datetime import datetime
    import urllib.parse

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    urls = []
    for filename in tqdm(filenames, desc="Uploading plots to s3"):
        # Set the filename using the current timestamp
        file_path_local = os.path.join(local_output_dir, f"{filename}.{file_format}")
        file_path_s3 = f'{project}/super_etl/{super_etl_name}/{pipeline}/{timestamp}/{filename}.png'

        # Create a session using your AWS credentials
        s3 = boto3.resource('s3')

        # Upload the file
        with open(file_path_local, "rb") as data:
            s3.Bucket(bucket).put_object(Key=file_path_s3, Body=data)

        # url encode
        url = f"https://{bucket}.s3.{bucket_region}.amazonaws.com/{urllib.parse.quote(file_path_s3)}"
        urls.append(url)

    return urls
