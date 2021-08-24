# Troubleshooting

This document contains some errors that may occur and possible reasons for them.

## No Image
### Error
>

### Possible reason
Note that every host type defines `ec2_image` in the [group_vars](../group_vars). This instance ID is different in different AWS regions. It will also change with image updates (e.g., when Amazon updates the Ubuntu version of their standard image).

Amazon descibes [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/finding-an-ami.html#finding-an-ami-console) how to find the AMI ID for your desired region, OS, architecture, etc.

You can also find the most up-to-date Ubuntu AMI ID with the following one-liner:
```bash
aws ec2 describe-images \
 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*" \
 --query 'Images[*].[ImageId,CreationDate]' --output text \
 | sort -k2 -r \
 | head -n1 \
 | awk '{print $1}'
```

## Snapshot ID
### Error

> Instance creation failed: snapshotId cannot be modified on root device

### Possible reason
Similar to the EC2 instance IDs, there are also snapshot IDs that differ between different instances and thus also between different AWS regions. For a given EC2 instance ID (see `No Image` error above), say `ami-05c26ae4789875080`, the following command outputs the snapshot ID:
```bash
aws ec2 describe-images --image-ids ami-05c26ae4789875080 --query "Images[0].BlockDeviceMappings[*].Ebs.SnapshotId"
```

This one needs to be specified in the [group_vars](../group_vars).
