# Copyright (c) 2025 Kamesh Sampath
# SPDX-License-Identifier: Apache-2.0
"""CLI entry points for hirc-duckdb-demo SQL operations.

Each command loads .env, reads required variables, and runs the
corresponding SQL file via `snow sql` subprocess. This eliminates
the error-prone `set -a && source .env && set +a` boilerplate.
"""

import os
import subprocess
import sys
from pathlib import Path

import click
from dotenv import load_dotenv


def _get_sql_dir() -> Path:
    """Return the sql/ directory relative to the project root."""
    # When installed via uv, the project root is the working directory
    sql_dir = Path.cwd() / "sql"
    if not sql_dir.is_dir():
        # Fallback: look relative to this file's package
        sql_dir = Path(__file__).parent.parent / "sql"
    return sql_dir


def _require_env(*names: str) -> dict[str, str]:
    """Read required env vars, abort with clear message if any missing."""
    load_dotenv()
    values = {}
    missing = []
    for name in names:
        val = os.environ.get(name, "").strip()
        if not val:
            missing.append(name)
        else:
            values[name] = val
    if missing:
        click.echo(f"Missing required .env variables: {', '.join(missing)}", err=True)
        click.echo("Ensure .env is populated (run snow-utils-pat first).", err=True)
        sys.exit(1)
    return values


def _run_snow_sql(
    sql_file: str,
    variables: dict[str, str],
    connection: str,
    dry_run: bool = False,
) -> None:
    """Run a SQL file via snow sql with templating variables."""
    sql_path = _get_sql_dir() / sql_file
    if not sql_path.exists():
        click.echo(f"SQL file not found: {sql_path}", err=True)
        sys.exit(1)

    cmd = [
        "snow",
        "sql",
        "-c",
        connection,
        "-f",
        str(sql_path),
        "--enable-templating",
        "ALL",
    ]

    for key, val in variables.items():
        cmd.extend(["--variable", f"{key}={val}"])

    if dry_run:
        click.echo("Would run:")
        click.echo(f"  snow sql -c {connection} -f {sql_path}")
        for key, val in variables.items():
            click.echo(f"    --variable {key}={val}")
        return

    click.echo(f"Running: snow sql -f {sql_file}")
    result = subprocess.run(cmd, env=os.environ)
    if result.returncode != 0:
        click.echo(f"Command failed with exit code {result.returncode}", err=True)
        sys.exit(result.returncode)


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
def setup(dry_run: bool) -> None:
    """Create demo database with USAGE grants and set external volume.

    Runs sql/demo_setup.sql with admin_role, database_name, sa_role,
    and external_volume_name from .env.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "ADMIN_ROLE",
        "DEMO_DATABASE",
        "SA_ROLE",
        "EXTERNAL_VOLUME_NAME",
    )
    _run_snow_sql(
        "demo_setup.sql",
        variables={
            "admin_role": env["ADMIN_ROLE"],
            "database_name": env["DEMO_DATABASE"],
            "sa_role": env["SA_ROLE"],
            "external_volume_name": env["EXTERNAL_VOLUME_NAME"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
    )


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
def load_data(dry_run: bool) -> None:
    """Create Iceberg table and load sample data.

    Runs sql/sample_data.sql with admin_role, database_name,
    and external_volume_name from .env.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "ADMIN_ROLE",
        "DEMO_DATABASE",
        "EXTERNAL_VOLUME_NAME",
    )
    _run_snow_sql(
        "sample_data.sql",
        variables={
            "admin_role": env["ADMIN_ROLE"],
            "database_name": env["DEMO_DATABASE"],
            "external_volume_name": env["EXTERNAL_VOLUME_NAME"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
    )


@click.command()
@click.option("--schema", default="PUBLIC", help="Schema name (default: PUBLIC)")
@click.option("--table", default="FRUITS", help="Table name (default: FRUITS)")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
def grant_rbac(schema: str, table: str, dry_run: bool) -> None:
    """Grant SELECT on Iceberg table to SA_ROLE.

    Runs sql/rbac.sql with admin_role, database_name, schema, table,
    and sa_role from .env.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "ADMIN_ROLE",
        "DEMO_DATABASE",
        "SA_ROLE",
    )
    _run_snow_sql(
        "rbac.sql",
        variables={
            "admin_role": env["ADMIN_ROLE"],
            "database_name": env["DEMO_DATABASE"],
            "schema": schema,
            "table": table,
            "sa_role": env["SA_ROLE"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
    )


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
def cleanup(dry_run: bool) -> None:
    """Drop demo database and all its tables.

    Runs sql/cleanup.sql with admin_role and database_name from .env.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "ADMIN_ROLE",
        "DEMO_DATABASE",
    )
    _run_snow_sql(
        "cleanup.sql",
        variables={
            "admin_role": env["ADMIN_ROLE"],
            "database_name": env["DEMO_DATABASE"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
    )
