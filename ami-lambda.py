import json
import datetime
import dateutil.parser
import logging
import re

import boto3
import botocore

#setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#config

ACCOUNT_ID = '<account number>'
KEEP_DAILY_DAYS = 3
KEEP_MONTHLY_DAYS = 90
MONTH_DAY= 1
IMAGE_CREATE_DRY_RUN = False


#ec2 boto client
ec2 = boto3.resource('ec2', region_name='ap-southeast-2')


#Removes images (list of ec2-image objects) that are older than min_oldness
#Also removes snapshots of AMIs
def remove_old_amis(images, min_oldness):
    logger.info("remove_old_amis()")
    logger.info("will attempt to remove amis: '%s' with min_oldness: '%s'", str(images), min_oldness)

    for ami in images:

        creation_date = dateutil.parser.parse(ami.creation_date, ignoretz=True)

        if creation_date < datetime.datetime.utcnow()-datetime.timedelta(days=min_oldness):
            #older
            logger.info("ami '%s' is older than '%s' days and will be deleted", ami.id, min_oldness)

            #remove ami
            logger.info("deregistering ami")
            ami.deregister()

            #remove any snapshot volumns that it owns
            for snapshot in ec2.snapshots.filter(OwnerIds=[ACCOUNT_ID]):

                #get the ami id (that the snapshot belongs to) from the snapshot's description
                r = re.match(r".*for (ami-.*) from.*", snapshot.description)

            if r:
                #r.groups()[0] will contain the ami id
                if r.groups()[0] == ami.id:
                    logger.info("found snapshot belonging to %s. snapshot with image_id %s will be deleted", ami.id, snapshot.snapshot_id)
                    snapshot.delete()           

        else:
            logger.info("ami '%s' is younger than %s days and will not be deleted", ami.id, KEEP_DAILY_DAYS)


#takes a list of EC2 instance IDs and creates AMIs
def create_amis(instances, cycle_tag):
    logger.info("create AMIs with cycle_tag: '%s'", cycle_tag)

    #creat image for each instance
    for instance in instances:

        for tag in instance.tags:
            if tag['Key'] == 'Name':
                instance_name = tag['Value']

        logger.info("creating image for ' %s' with name: %s",instance.id, instance_name)

        try:
            utc_now = datetime.datetime.utcnow()
            name = '%s-%s %s/%s/%s %s-%s-%sUTC' % (cycle_tag,
                                                   instance_name, 
                                                   utc_now.day, 
                                                   utc_now.month, 
                                                   utc_now.year, 
                                                   utc_now.hour, 
                                                   utc_now.minute, 
                                                   utc_now.second)
            #AMIs names cannot contain ',' 
            name = name.replace(',', '')
            
            image = instance.create_image(
                DryRun=IMAGE_CREATE_DRY_RUN,
                Name=name,
                Description='AMI of ' + instance.id + ' created with Lambda function',
                NoReboot=True
            )

            logger.info('call to create_image succeeded')

            #create tag(s)
            image.create_tags( Tags=[{'Key': 'ami-cycle', 'Value': cycle_tag}])

        except botocore.exceptions.ClientError as err:
            logger.info('caught exception: Error message: %s', err)



def lambda_handler(event, context):

    #Daily
    #filter for AMIs tagged with ami-cycle=daily and remove if necessary
    logger.info('filtering for amis with tag ami-cycle=daily')
    ami_filter = [{'Name':'tag:ami-cycle', 'Values':['daily']}]
    images = list(ec2.images.filter(Filters=ami_filter))  

    if images:
        image_ids = [ img.id for img in images ]
        logger.info("images tagged with ami-cycle=daily: %s", ', '.join(image_ids))
        remove_old_amis(images, KEEP_DAILY_DAYS)
    else:
        logger.info('no images were found with ami-cycle=true')

    #Monthly
    #filter for AMIs tagged with ami-cycle=monthly and remove if necessary
    logger.info('filtering for amis with tag ami-cycle=monthly')
    ami_filter = [{'Name':'tag:ami-cycle', 'Values':['monthly']}]
    images = list(ec2.images.filter(Filters=ami_filter))  

    if images:
        image_ids = [ img.id for img in images ]
        logger.info("images tagged with ami-cycle=monthly: %s", ', '.join(image_ids))
        remove_old_amis(images, KEEP_MONTHLY_DAYS)
    else:
        logger.info('no images were found with ami-cycle=monthly')


    #filter for instances tagged with ami-creation=true
    ec2_filter = [{'Name':'tag:ami-creation', 'Values':['true']}]
    instances = list(ec2.instances.filter(Filters=ec2_filter))

    #create AMIs with ami-cycle=daily unless it's the nominated day of the month
    # to create monthly AMIs
    CYCLE_TAG = ''
    
    day = datetime.datetime.utcnow().day
    logger.info("today is day '%s'. COPY_ON_MONTH_DAY is set to '%s'", day, COPY_ON_MONTH_DAY)
    
    if day == MONTH_DAY:
        CYCLE_TAG = 'monthly'
    else:
        CYCLE_TAG = 'daily'
    
    logger.info("ami-cycle tag set to '%s'", CYCLE_TAG)

    create_amis(instances, cycle_tag=CYCLE_TAG)
    
    logger.info('lambda complete')
    
    return {}
