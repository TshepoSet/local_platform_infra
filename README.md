# 🚀 Local Platform Infra

[![License:
MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Podman](https://img.shields.io/badge/Container-Podman-blue) ![Traefik
v3](https://img.shields.io/badge/Proxy-Traefik_v3-green)
![Platform](https://img.shields.io/badge/Type-Local_Dev_Platform-purple)

A reusable local development platform built with **Podman + Traefik**
that gives you:

-   Clean service routing\
-   Trusted HTTPS locally\
-   Zero port conflicts\
-   Structured microservice development

If you're building multiple services and you're tired of chaos --- this
is your base layer.

------------------------------------------------------------------------

## 💡 Why This Exists

Local development often turns into:

-   localhost:3000
-   localhost:5432
-   localhost:6379
-   6 terminals open
-   Random port conflicts
-   No HTTPS
-   Every project configured differently

This project fixes that.

It provides a consistent internal platform that runs on your machine.

Everything goes through one edge router.\
Everything has a predictable hostname.\
Everything runs the same way.

------------------------------------------------------------------------

## 🧠 What This Is

This is not an app.

It's a local platform layer that:

-   Runs services via Podman
-   Routes traffic through Traefik
-   Uses mkcert for trusted HTTPS
-   Provides templates for new services
-   Standardizes how infrastructure runs locally

Think of it as:

> A mini internal developer platform --- on your laptop.

------------------------------------------------------------------------

## 🏗 Architecture Overview

Instead of:

localhost:3000\
localhost:5001\
localhost:8080

You use:

app.localhost\
db.localhost\
redis.localhost\
traefik.localhost

All over HTTPS.

Flow:

Browser\
↓\
Traefik (Reverse Proxy)\
↓\
Service Container

Clean. Predictable. Scalable.

------------------------------------------------------------------------

## 📁 Project Structure

core/ → Traefik + platform configuration\
services/ → All running services\
templates/service/ → Template for creating new services\
tools/ → Helper scripts\
Makefile → Platform control commands

------------------------------------------------------------------------

## 🧰 Requirements

Install:

-   Podman
-   podman-compose
-   mkcert

This project uses rootless Podman by default.

------------------------------------------------------------------------

## 🔐 First-Time Setup

### Install local certificate authority

mkcert -install

### Generate development certificates

mkcert pgadmin.localhost redis.localhost db.localhost traefik.localhost

Move generated .pem files into:

core/certs/

You only need to do this once.

------------------------------------------------------------------------

## ▶️ Running The Platform

Start everything:

make up

Stop everything:

make down

View running containers:

make ps

Rebuild without cache:

make rebuild

Sync routing changes:

make routes

The Makefile is your control center.

------------------------------------------------------------------------

## ➕ Adding a New Service

1.  Copy the template:

cp -r templates/service services/myapp

2.  Update:
    -   Service name
    -   Hostname
    -   Image
    -   Routing config
3.  Sync routes:

make routes

4.  Restart platform:

make up

Now your service is available at:

myapp.localhost

Over HTTPS.

------------------------------------------------------------------------

## 🎯 Who This Is For

-   Backend developers building multiple services\
-   Platform engineers experimenting locally\
-   Full-stack developers who want HTTPS\
-   Teams that want consistent local environments\
-   Anyone tired of port chaos

If you care about structure, this is for you.

------------------------------------------------------------------------

## 🧩 Design Philosophy

This project enforces one principle:

Everything runs through the platform.

No random containers.\
No ad-hoc routing.\
No inconsistent setup per project.

Local development should resemble production --- structurally.

------------------------------------------------------------------------

## 📜 License

This project is licensed under the MIT License.\
See the LICENSE file for details.

------------------------------------------------------------------------

## 👤 Author

Built by Tshepo Setshedi
