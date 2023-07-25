start:
	docker-compose run --rm app sh -c "python manage.py start_server 0.0.0.0:8000"

test:
	docker-compose run --rm app sh -c "python manage.py test"

flake:
	docker-compose run --rm app sh -c "flake8"

docker_run:
	docker-compose run --rm app sh -c "$(arg)"