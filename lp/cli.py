"""The preferred developer interface; orchestration lives in Platform."""
from pathlib import Path
import subprocess
from typing import Optional

import typer
import yaml

from .platform import Platform
from .services import add_service

app = typer.Typer(help="Local development with Podman, Traefik and predictable HTTPS.",
                  no_args_is_help=True, add_completion=False, pretty_exceptions_enable=False)


@app.callback()
def configure(ctx: typer.Context, root: Optional[Path] = typer.Option(None, help="Infrastructure checkout (or LP_ROOT).")):
    ctx.obj = root


def platform(ctx):
    return Platform(ctx.obj)


@app.command()
def setup(ctx: typer.Context):
    """Validate dependencies, create proxy network and prepare trusted HTTPS."""
    platform(ctx).setup()
    typer.echo("Platform setup ready.")


@app.command()
def up(ctx: typer.Context, service: Optional[str] = typer.Argument(None)):
    """Start all services, or one service, with platform prerequisites."""
    platform(ctx).up(service)


@app.command()
def down(ctx: typer.Context, service: Optional[str] = typer.Argument(None)):
    """Stop the platform, or just one service. Keep persistent volumes."""
    platform(ctx).down(service)


@app.command()
def add(ctx: typer.Context, service: str,
        path: Optional[Path] = typer.Option(None, help="External application build context."),
        image: Optional[str] = typer.Option(None, help="Registry image, or optional local build tag."),
        dockerfile: Optional[str] = typer.Option(None, help="Dockerfile relative to --path."),
        port: Optional[int] = typer.Option(None, min=1, max=65535, help="Internal HTTP port; required for local builds.")):
    """Register an external application or registry image."""
    add_service(platform(ctx).root, service, image=image, context=path, dockerfile=dockerfile, port=port)
    typer.echo(f"Start it with: lp up {service.lower()}")


@app.command()
def status(ctx: typer.Context):
    """Show service states, URLs, proxy network and certificate readiness."""
    platform(ctx).status()


@app.command()
def logs(ctx: typer.Context, service: str,
         follow: bool = typer.Option(True, "--follow/--no-follow", help="Follow live output.")):
    """Show a registered service's logs (follow by default)."""
    platform(ctx).logs(service, follow)


@app.command()
def restart(ctx: typer.Context, service: str):
    """Recreate and start the service with platform prerequisites."""
    platform(ctx).restart(service)


@app.command()
def rebuild(ctx: typer.Context, service: str):
    """Build without cache, then recreate and start the service."""
    platform(ctx).rebuild(service)


@app.command()
def remove(ctx: typer.Context, service: str):
    """Stop and unregister a service. Preserve application source and volumes."""
    platform(ctx).remove(service)


@app.command("help")
def help_command(ctx: typer.Context):
    """Show concise command help."""
    typer.echo(ctx.parent.get_help())


def main():
    try:
        app()
    except (ValueError, OSError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        message = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            message += "\n" + exc.stderr.strip()
        typer.echo(f"Error: {message}", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    main()
