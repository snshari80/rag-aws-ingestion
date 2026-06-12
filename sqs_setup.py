import json
import logging

import boto3  # AWS SDK for SQS queue creation
from botocore.exceptions import ClientError

from config import (
    AWS_REGION,
    SQS_VISIBILITY_TIMEOUT,
    SQS_MAX_RECEIVE_COUNT,
    MAIN_QUEUE_NAME,
    DLQ_NAME,
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_queue():
    sqs = boto3.client("sqs", region_name=AWS_REGION)

    print("\n" + "*" * 60)
    print("\nRAG Pipeline - SQS Setup")
    print("\n" + "=" * 60)

    # -------------------------------
    # [1/4] Create DLQ
    # -------------------------------
    print(f"\n[1/4] Create DLQ - Dead Letter Queue: {DLQ_NAME}")

    try:
        dlq_response = sqs.create_queue(
            QueueName=DLQ_NAME,
            Attributes={
                "MessageRetentionPeriod": str(14 * 24 * 3600),
            },
        )
        dlq_url = dlq_response["QueueUrl"]

    except ClientError as e:
        if "QueueAlreadyExists" in str(e):
            dlq_url = sqs.get_queue_url(QueueName=DLQ_NAME)["QueueUrl"]
            print(f"ℹ️  DLQ already exists: {dlq_url}")
        else:
            raise

    # Get DLQ ARN
    dlq_attrs = sqs.get_queue_attributes(
        QueueUrl=dlq_url,
        AttributeNames=["QueueArn"],
    )
    dlq_arn = dlq_attrs["Attributes"]["QueueArn"]
    print(f"DLQ ARN: {dlq_arn}")

    # -------------------------------
    # [2/4] Create Main Queue
    # -------------------------------
    print(f"\n[2/4] Create Main Queue: {MAIN_QUEUE_NAME}")

    redrive_policy = json.dumps(
        {
            "maxReceiveCount": str(SQS_MAX_RECEIVE_COUNT),
            "deadLetterTargetArn": dlq_arn,
        }
    )

    try:
        main_response = sqs.create_queue(
            QueueName=MAIN_QUEUE_NAME,
            Attributes={
                "VisibilityTimeout": str(SQS_VISIBILITY_TIMEOUT),
                "MessageRetentionPeriod": str(4 * 24 * 3600),
                "RedrivePolicy": redrive_policy,
            },
        )
        main_url = main_response["QueueUrl"]

        # Get Main Queue ARN
        main_attrs = sqs.get_queue_attributes(
            QueueUrl=main_url,
            AttributeNames=["QueueArn"],
        )
        main_arn = main_attrs["Attributes"]["QueueArn"]
        print(f"Main Queue ARN: {main_arn}")

    except ClientError as e:
        if "QueueAlreadyExists" in str(e):
            main_url = sqs.get_queue_url(QueueName=MAIN_QUEUE_NAME)["QueueUrl"]
            print(f"ℹ️  Main queue already exists: {main_url}")

            main_attrs = sqs.get_queue_attributes(
                QueueUrl=main_url,
                AttributeNames=["QueueArn"],
            )
            main_arn = main_attrs["Attributes"]["QueueArn"]
        else:
            raise

    # -------------------------------
    # [3/4] Set S3 → SQS Policy
    # -------------------------------
    print("\n[3/4] Setting queue policy to allow S3 to publish...")

    queue_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "s3.amazonaws.com"},
                    "Action": "sqs:SendMessage",
                    "Resource": main_arn,
                    "Condition": {
                        "StringLike": {
                            "aws:SourceArn": "arn:aws:s3:::*",
                        }
                    },
                }
            ],
        }
    )

    sqs.set_queue_attributes(
        QueueUrl=main_url,
        Attributes={"Policy": queue_policy},
    )
    print("✅ S3 → SQS publish permission set")

    # -------------------------------
    # [4/4] Summary
    # -------------------------------
    print("\n[4/4] Summary")
    print("=" * 60)

    print(f"\nMain Queue URL : {main_url}")
    print(f"DLQ URL        : {dlq_url}")
    print(f"Visibility     : {SQS_VISIBILITY_TIMEOUT}s")
    print(f"Max retries    : {SQS_MAX_RECEIVE_COUNT} (then → DLQ)")

    print("\n" + "─" * 60)
    print("Copy these into your .env file:")
    print("─" * 60)

    print(f'\nSQS_QUEUE_URL="{main_url}"')
    print(f'SQS_DLQ_URL="{dlq_url}"')

    return main_url, dlq_url


if __name__ == "__main__":
    create_queue()