from datasette import hookimpl


@hookimpl
def register_commands(cli):
    from .cli import cli as dclient_cli

    cli.add_command(dclient_cli, name="client")
