# Automated AMI creation and removal
(WIP: needs to run Ec2 command to dump db and store in bucket)

Disaster Recovery solution for using CloudWatch rules to trigger an event on a lambda function which creates/removes AMIs.

_note that because lambda is not available in the ap-southeast-2 region (yet), all these resources should be deployed in us-east-1_
### Components of the DR system:

##### S3 
An S3 bucket is required to store the code for the Lambda function

##### CloudFormation 
A CloudFormation template contains these resources:
- IAM role for the Lambda function which allows it to log to a CloudWatch Logs group and perform all the actions needed to create/remove AMIs
- Lambda function that creates/removes AMIs

##### CloudWatch rule
The DR system requires the creation of a rule so that the lambda function can be triggered each day.
As yet, CloudFormation does not support the creation of CloudWatch rules. The event.sh script will allow the creation (and optionally the removal) of the rule.

### Create resources on AWS

1. Make code for Lambda function available in S3 Bucket

```bash
#create bucket
aws s3 mb --region us-east-1 s3://<bucket name>

#zip up code
zip ami-lambda.zip ami-lambda.py

#upload zip to bucket
aws s3 cp --region us-east-1 ami-lambda.zip s3://<bucket name>

#clean up 
rm ami-lambda.zip
```
2. Create CloudFormation stack using the `dr-cloudformation.json` template.
Note the parameters that point to the bucket and zip file that was created in previous step
```bash
aws cloudformation create-stack --region us-east-1 \
                                --stack-name DisasterRecoveryBackupSystem \
                                --template-body file://dr-cloudformation.json \
                                --parameters ParameterKey=LambdaBucket,ParameterValue=<bucket name> \
                                ParameterKey=LambdaKey,ParameterValue=ami-lambda.zip \
                                --capabilities CAPABILITY_IAM
```

3. Create the CloudWatch rule

Use the event.sh script to create the rule
```bash
./event.sh create
```

### Tear down
The setup can be torn down if needed without affecting the AMIs that have been created
1. Delete the stack
2. run `./event remove`
3. remove the s3 bucket
