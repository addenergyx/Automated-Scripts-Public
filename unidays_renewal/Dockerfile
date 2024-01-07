# Dockerfile, Image, Container

# Lambda images are not made from python:3.8 Docker image.
# Instead they should be made from public.ecr.aws/lambda/python:3.8.
# The lambda container images must be specially constructed to work correctly with lambda.

# login request doesn't work with aws image
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.8
# FROM --platform=linux/amd64 python:3.8

RUN pip install pipenv

ENV PROJECT_DIR /usr/local/src/code

WORKDIR ${PROJECT_DIR}

COPY ./unidays_renewal/Pipfile ./unidays_renewal/Pipfile.lock ${PROJECT_DIR}/

RUN pip install --upgrade cython
RUN pip install --upgrade pip

RUN pipenv install --system --deploy

# COPY ./unidays_renewal/app.py ${LAMBDA_TASK_ROOT}
# COPY ../common ${LAMBDA_TASK_ROOT}/common

COPY ../common ${PROJECT_DIR}/common
COPY ./unidays_renewal ${PROJECT_DIR}/unidays_renewal

# Getting access denied in aws as not same user as locally
RUN chmod -R 777 .

# setting the CMD to your handler file_name.function_name
COPY ./unidays_renewal/app.py ${LAMBDA_TASK_ROOT}/unidays_renewal/
COPY ../common ${LAMBDA_TASK_ROOT}/common
CMD [ "unidays_renewal/app.handler" ]

# CMD [ "/bin/sh" , "-c" , "cd unidays_renewal && python -u app.py" ]









