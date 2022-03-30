FROM python:3

ADD quickStartprueba.py .

RUN pip install pydrive
RUN pip install mysql.connector
RUN pip install simplegmail
RUN pip install pysimplegui

CMD [ "python", "./quickStartprueba.py" ]