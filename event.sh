#!/bin/bash


REGION=us-east-1
RULE_NAME=disaster-recovery-lambda
EXPRESSION="cron(0 16 * * ? *)"

#The ARN of the lambda the rule will target (single and double quotes are necessary)
LAMBDA_ARN='"arn:aws:lambda:us-east-1:670548263515:function:DR-Manage-AMIs"'

remove_event()
{
  echo "removing rule..."

  aws events remove-targets --region $REGION \
                            --rule $RULE_NAME \
                            --ids "1" \
 

  aws events delete-rule --region $REGION \
                         --name $RULE_NAME \

}


create_event()
{
  echo "creating rule..."

  aws events put-rule --region $REGION \
                      --name $RULE_NAME \
                      --schedule-expression "$EXPRESSION" \

 
  aws events put-targets --region $REGION \
                         --targets '{"Id": "1", "Arn": '$LAMBDA_ARN', "Input": "{\"abc\":\"xyz\"}"}' \
                         --rule $RULE_NAME \
}


case "$1" in

    create)
    create_event
    exit 0
    ;;
    remove)
    remove_event
    exit 0
    ;;
    *)
    echo "Usage: supply 'create' or 'remove'"
    exit 0
    ;;
esac

