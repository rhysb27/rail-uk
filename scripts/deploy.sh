#!/bin/bash

cd /Users/rhysb/Repositories/rail-uk
rm deploy.zip

echo "Zipping files into deployment package: deploy.zip..."
zip -uX deploy.zip lambda_entry.py
zip -ur deploy.zip res
zip -ur deploy.zip rail_uk -x *__pycache__*

echo "Deploying package to Lambda function..."
aws lambda update-function-code --function-name rail-uk --zip-file fileb://deploy.zip --profile personal

echo "Done."
