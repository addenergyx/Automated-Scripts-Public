# Dockerfile, Image, Container

# Lambda images are not made from python:3.8 Docker image.
# Instead they should be made from public.ecr.aws/lambda/python:3.8.
# The lambda container images must be specially constructed to work correctly with lambda.

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.8

RUN pip install pipenv

ENV PROJECT_DIR /usr/local/src/code

WORKDIR ${PROJECT_DIR}

COPY ./plutus_tracker/Pipfile ./plutus_tracker/Pipfile.lock ${PROJECT_DIR}/

RUN pip install --upgrade cython
RUN pip install --upgrade pip

RUN pipenv install --system --deploy

# Pandas in pipfile not working
#RUN pip install pandas

COPY ../common ${PROJECT_DIR}/common/
COPY ../plutus_api ${PROJECT_DIR}/plutus_api/
COPY ./plutus_tracker ${PROJECT_DIR}/plutus_tracker/
#
# COPY ./plutus_tracker/app.py ${PROJECT_DIR}/
# COPY ./plutus_tracker/app.py ./

# Getting access denied in aws as not same user as locally
RUN chmod -R 777 .

# CMD [ "/bin/sh" , "-c" , "cd plutus_tracker && python -u plutus.py" ]

# WORKDIR ${PROJECT_DIR}/plutus_tracker/

COPY ./plutus_tracker/app.py ${LAMBDA_TASK_ROOT}

# setting the CMD to your handler file_name.function_name
CMD [ "app.handler" ]
