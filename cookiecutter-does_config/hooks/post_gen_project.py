import subprocess

def get_latest_ami(default_ubuntu_ami="ami-08481eff064f39a84"):
    # TODO [nku]: this does not work because in the way I've installed cookiecutter I cannot use the aws cli
    return default_ubuntu_ami

#    try:
#        proc_aws = subprocess.Popen([
#            "aws",
#            "ec2",
#            "describe-images",
#            "--filters",
#            "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*",
#            "--query",
#            "Images[*].[ImageId,CreationDate]",
#            "--output",
#            "text"
#        ], stdout=subprocess.PIPE)
#
#        proc_sort = subprocess.Popen([
#            "sort",
#            "-k2",
#            "-r"
#        ], stdin=proc_aws.stdout, stdout=subprocess.PIPE)
#
#        proc_aws.stdout.close()
#
#        proc_head = subprocess.Popen([
#            "head",
#            "-n1"
#        ], stdin=proc_sort.stdout, stdout=subprocess.PIPE)
#
#        proc_sort.stdout.close()
#
#        proc_awk = subprocess.Popen([
#            "awk",
#            "{print $1}"
#        ], stdin=proc_head.stdout, stdout=subprocess.PIPE)
#
#        ubuntu_ami = proc_awk.communicate()[0].decode().rstrip()
#    except:
#        print(f"WARNING: Failed to get latest ubuntu AMI, using {default_ubuntu_ami}")
#        ubuntu_ami = default_ubuntu_ami
#
#    return ubuntu_ami


def get_volume_snapshot():
    return 'snap-0b8d7894c93b6df7a'
    # TODO [nku] not implemented at the moment

    # Find the SnapshotId for this instance
    #try:
    #    snapshot_id = literal_eval(subprocess.check_output([
    #        "aws",
    #        "ec2",
    #        "describe-images",
    #        "--image-ids",
    #        d["ec2_image_id"],
    #        "--query",
    #        "Images[0].BlockDeviceMappings[*].Ebs.SnapshotId"
    #    ]).decode())[0]
    #    d["snapshot_id"] = snapshot_id
    #except:
    #    print(f"WARNING: could not fetch snapshot id for {d['ec2_image_id']}")
    #    pass

# set the ec2_ami and ec2_volume_snapshot to the latest version if specified

LATEST_AMI_TAG = "<LATEST-AMI>"
LATEST_SNAPSHOT_TAG = "<LATEST-VOLUME-SNAPSHOT>"

filepath = "group_vars/{{ cookiecutter.host_name }}/main.yml"
with open(filepath, 'r') as read_file:
    lines = read_file.readlines()
    with open(filepath, 'w') as write_file:
        for line in lines:
            if LATEST_AMI_TAG in line:
                write_file.write(line.replace(LATEST_AMI_TAG, get_latest_ami()))
            elif LATEST_SNAPSHOT_TAG in line:
                 write_file.write(line.replace(LATEST_SNAPSHOT_TAG, get_volume_snapshot()))
            else:
                write_file.write(line)
