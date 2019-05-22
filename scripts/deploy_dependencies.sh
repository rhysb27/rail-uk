#!/bin/bash
cd /Users/rhysb/Repositories/rail-uk

PY_DIR='build/python/lib/python3.6/site-packages'
mkdir -p $PY_DIR                                            # Create temporary build directory
pip install -r requirements.txt --no-deps -t $PY_DIR        # Install packages into the target directory
cd build
zip -r ../dependencies.zip .                                # Zip files
cd ..
rm -r build                                                 # Remove temporary directory

echo "Deploying package to Lambda function..."
aws lambda publish-layer-version --layer-name dependencies --zip-file fileb://dependencies.zip --profile personal

echo "Done."
