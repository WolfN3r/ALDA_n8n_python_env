.PHONY: up down logs build env x11-init init

# Sestavení a spuštění kontejnerů na pozadí
down:
	docker-compose down

up:
	docker-compose up -d --build

# Sleduje logy všech služeb
logs:
	docker-compose logs -f

# Pouze build image
build:
	docker-compose build

# Vytvoří .env soubor s proměnnou DISPLAY (pro Linux/macOS)
#env:
#	@echo DISPLAY=:0 > .env

# Povolí X11 pro root uživatele a vytvoří .env (pouze na Linux/macOS)
x11-init: env
	-@xhost +local:root || true

# Příprava projektu (env + x11-init)
init: x11-init