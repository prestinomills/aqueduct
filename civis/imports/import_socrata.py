"""
An Import Socrata Template for Deployment on Civis Platform

Author: @sherryshenker
"""
import logging
import os
from datetime import datetime

import civis
from sodapy import Socrata

from socrata_helpers import (
    _read_paginated,
    _store_and_attach_dataset,
    write_and_attach_jsonvalue,
    _store_and_attach_metadata,
)

LOG = logging.getLogger(__name__)


def main(
    dataset_id,
    table_name,
    database,
    socrata_username,
    socrata_password,
    where_clause,
    existing_table_rows="drop",
):
    """
    Read in dataset from Socrata and write output to Platform
    Parameters
    --------
    dataset_id: str
        Socrata dataset identifier
    table_name: str, optional
        destination table in Platform (schema.table)
    database: str, optional
        destination database in Platform
    socrata_username: str, optional
        username for socrata account, required for private data sets
    socrata_password: str, optional
        password for socrata account, required for private data sets
    where_clause: str, optional
        SoQL for filtering dataset
    existing_table_rows: str, optional
        options to pass to dataframe_to_civis command

    Outputs
    ------
    Adds data as file output
    and, if table_name and database are specified, writes data to Platform
    """

    socrata_client = Socrata(
        "data.lacity.org", None, username=socrata_username, password=socrata_password
    )

    socrata_client.timeout = 50

    raw_metadata = socrata_client.get_metadata(dataset_id)

    dataset = _read_paginated(socrata_client, dataset_id, where=where_clause)

    civis_client = civis.APIClient()

    if dataset.empty:
        msg = f"No rows returned for dataset {dataset_id}."
        LOG.warning(msg)
        write_and_attach_jsonvalue(json_value=msg, name="Error", client=civis_client)
    else:
        data_file_name = (
            f"{dataset_id}_extract_{datetime.now().strftime('%Y-%m-%d')}.csv"
        )
        file_id = _store_and_attach_dataset(
            client=civis_client, df=dataset, filename=data_file_name
        )
        LOG.info(f"add the {file_id}")

        if table_name:
            # Optionally start table upload
            LOG.info(f"Storing data in table {table_name} on database {database}")
            print("writing table")
            run_id = os.environ["CIVIS_RUN_ID"]
            job_id = os.environ["CIVIS_JOB_ID"]
            dataset["civis_job_id"] = job_id
            dataset["civis_run_id"] = run_id
            table_upload = civis.io.dataframe_to_civis(
                dataset,
                database=database,
                table=table_name,
                existing_table_rows=existing_table_rows,
            ).result()
            LOG.info(f"using {table_upload}")

    # Parse raw_metadata to extract useful fields and attach both raw and
    # cleaned metadata as script outputs
    metadata_file_name = (
        f"{dataset_id}_metadata_{datetime.now().strftime('%Y-%m-%d')}.json"
    )

    metadata_paths = {
        "Proposed access level": "metadata.custom_fields.Proposed Access Level.Proposed Access Level",  # noqa: E501
        "Description": "description",
        "Data updated at": "rowsUpdatedAt",
        "Data provided by": "tableAuthor.screenName",
    }

    _, clean_metadata = _store_and_attach_metadata(
        client=civis_client,
        metadata=raw_metadata,
        metadata_paths=metadata_paths,
        filename=metadata_file_name,
    )

    if table_name:
        sql = f'COMMENT ON TABLE {table_name} IS \'{clean_metadata["Description"]}\''
        civis.io.query_civis(
            sql, database=database, polling_interval=2, client=civis_client
        ).result()


if __name__ == "__main__":
    dataset_id = os.environ["dataset_id"]
    existing_table_rows = os.environ["existing_table_rows"]
    if "table_name" in list(os.environ.keys()) and "database" in list(
        os.environ.keys()
    ):
        table_name = os.environ["table_name"]
        database = os.environ["database"]
    else:
        table_name = None
        database = None
    if "socrata_username" in list(os.environ.keys()):
        socrata_username = os.environ["socrata_username"]
        socrata_password = os.environ["socrata_password"]
    else:
        socrata_username = None
        socrata_password = None
    if "where_clause" in list(os.environ.keys()):
        where_clause = os.environ["where_clause"]
    else:
        where_clause = None
    main(
        dataset_id,
        table_name,
        database,
        socrata_username,
        socrata_password,
        where_clause,
        existing_table_rows,
    )
