#!/bin/bash
python manage.py migrate
python manage.py runserver ${GUNICORN_BIND} --noreload