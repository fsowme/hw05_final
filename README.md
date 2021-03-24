
Yatube
======

Educational project made with Django-framework. Simple social network.
There are tests, pagination, image loading, cache, registration, subscriptions, form validation.

To run:

* clone this repository
  ```
  git clone git@github.com:fsowme/hw05_final.git
  ```

* open new folder with this project, create and activate virual environment
  ```
  cd hw05_final
  python -m venv venv
  source venv/bin/activate
  ```

* install all dependencies
  ```
  pip install -r requirements.txt
  ```

* make migrations and migrate
  ```
  python manage.py makemigrations && python manage.py migrate

  ```

* run server and open index page http://127.0.0.1:8000
  ```
  python manage.py runserver
  ```
