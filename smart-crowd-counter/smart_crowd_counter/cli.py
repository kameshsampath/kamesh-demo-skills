# Copyright (c) 2026 Kamesh Sampath
# SPDX-License-Identifier: Apache-2.0
"""CLI entry points for smart-crowd-counter SQL operations.

Each command loads .env, reads required variables, and runs the
corresponding SQL file via `snow sql` subprocess. This eliminates
the error-prone `set -a && source .env && set +a` boilerplate.

NOTE: ``uv run --project <SKILL_DIR>`` changes CWD to the skill
install directory, so the user's project ``.env`` and ``sql/``
won't be found via ``Path.cwd()``.  Every command therefore
accepts ``--env-file`` (path to ``.env``) and ``--sql-dir``
(path to the ``sql/`` folder in the user's project).
"""

import os
import subprocess
import sys
from pathlib import Path

import click
from dotenv import load_dotenv


def _get_sql_dir(sql_dir: str | None = None) -> Path:
    """Return the sql/ directory.

    Priority:
    1. Explicit ``sql_dir`` argument (from ``--sql-dir`` CLI option)
    2. ``sql/`` under the current working directory
    3. ``sql/`` relative to this Python package (skill install dir)
    """
    if sql_dir:
        p = Path(sql_dir)
        if p.is_dir():
            return p
        click.echo(f"Specified --sql-dir not found: {p}", err=True)
        sys.exit(1)
    cwd_sql = Path.cwd() / "sql"
    if cwd_sql.is_dir():
        return cwd_sql
    return Path(__file__).parent.parent / "sql"


def _require_env(*names: str, env_file: str | None = None) -> dict[str, str]:
    """Read required env vars, abort with clear message if any missing.

    ``env_file`` lets callers point at the user's project ``.env``
    when CWD differs from the project directory.

    Uses ``override=True`` so the .env file always wins over any
    pre-existing environment variables (e.g. empty values exported
    by an earlier ``set -a && source .env && set +a``).
    """
    if env_file:
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        val = os.environ.get(name, "").strip()
        if not val:
            missing.append(name)
        else:
            values[name] = val
    if missing:
        click.echo(f"Missing required .env variables: {', '.join(missing)}", err=True)
        hint = f" (searched: {env_file})" if env_file else ""
        click.echo(f"Ensure .env is populated with Snowflake connection details.{hint}", err=True)
        sys.exit(1)
    return values


# -- shared click options for env-file and sql-dir -------------------------

_env_file_option = click.option(
    "--env-file",
    default=None,
    type=click.Path(exists=True),
    help="Path to .env file (needed when --project changes CWD)",
)
_sql_dir_option = click.option(
    "--sql-dir",
    default=None,
    type=click.Path(exists=True),
    help="Path to sql/ directory (needed when --project changes CWD)",
)


def _run_snow_sql(
    sql_file: str,
    variables: dict[str, str],
    connection: str,
    dry_run: bool = False,
    sql_dir: str | None = None,
) -> None:
    """Run a SQL file via snow sql with templating variables."""
    sql_path = _get_sql_dir(sql_dir) / sql_file
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
@click.option("--admin-role", required=True, help="Admin role (from manifest, NOT .env)")
@click.option("--demo-role", required=True, help="Demo role to create (from manifest)")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
@_env_file_option
@_sql_dir_option
def create_role(admin_role: str, demo_role: str, dry_run: bool,
                env_file: str | None, sql_dir: str | None) -> None:
    """Create demo role, database, and grant privileges.

    Runs sql/create_role.sql with admin_role to:
    - Create the demo role and grant it to the current user
    - Create the database and transfer ownership to demo_role
    - Grant USAGE + OPERATE on warehouse to demo_role
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE",
        "DEMO_DATABASE",
        env_file=env_file,
    )
    _run_snow_sql(
        "create_role.sql",
        variables={
            "admin_role": admin_role,
            "demo_role": demo_role,
            "snowflake_user": env["SNOWFLAKE_USER"],
            "database": env["DEMO_DATABASE"],
            "warehouse": env["SNOWFLAKE_WAREHOUSE"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
        sql_dir=sql_dir,
    )


@click.command()
@click.option("--demo-role", required=True, help="Demo role (from manifest)")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
@_env_file_option
@_sql_dir_option
def setup(demo_role: str, dry_run: bool,
          env_file: str | None, sql_dir: str | None) -> None:
    """Create demo schema, stage, and AI-powered view.

    Runs sql/setup.sql with demo_role (DB owner, from manifest),
    database, schema, stage, and ai_model from .env.
    The database must already exist (created by scc-create-role).
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "DEMO_DATABASE",
        "DEMO_SCHEMA",
        "DEMO_STAGE",
        "AI_MODEL",
        env_file=env_file,
    )
    _run_snow_sql(
        "setup.sql",
        variables={
            "demo_role": demo_role,
            "database": env["DEMO_DATABASE"],
            "schema": env["DEMO_SCHEMA"],
            "stage": env["DEMO_STAGE"],
            "ai_model": env["AI_MODEL"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
        sql_dir=sql_dir,
    )


@click.command()
@click.option("--admin-role", required=True, help="Admin role (from manifest, NOT .env)")
@click.option("--demo-role", required=True, help="Demo role to grant warehouse access")
@click.option("--warehouse", required=True, help="Warehouse name to create")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
@_env_file_option
@_sql_dir_option
def create_warehouse(admin_role: str, demo_role: str, warehouse: str, dry_run: bool,
                     env_file: str | None, sql_dir: str | None) -> None:
    """Create a warehouse and grant access to the demo role.

    Runs sql/create_warehouse.sql with admin_role to create the warehouse,
    then grants USAGE + OPERATE to demo_role.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        env_file=env_file,
    )
    _run_snow_sql(
        "create_warehouse.sql",
        variables={
            "admin_role": admin_role,
            "demo_role": demo_role,
            "warehouse": warehouse,
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
        sql_dir=sql_dir,
    )


@click.command()
@click.option("--demo-role", required=True, help="Demo role that owns the database (from manifest/.env)")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
@_env_file_option
@_sql_dir_option
def cleanup(demo_role: str, dry_run: bool,
            env_file: str | None, sql_dir: str | None) -> None:
    """Drop demo database and all its objects.

    Runs sql/cleanup.sql with demo_role (the DB owner) to drop the database.
    The demo role owns the database so no admin role is needed for this step.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "DEMO_DATABASE",
        env_file=env_file,
    )
    _run_snow_sql(
        "cleanup.sql",
        variables={
            "demo_role": demo_role,
            "database": env["DEMO_DATABASE"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
        sql_dir=sql_dir,
    )


@click.command()
@click.option("--admin-role", required=True, help="Admin role (from manifest, NOT .env)")
@click.option("--demo-role", required=True, help="Demo role to drop (from manifest)")
@click.option("--dry-run", is_flag=True, help="Preview command without executing")
@_env_file_option
@_sql_dir_option
def cleanup_role(admin_role: str, demo_role: str, dry_run: bool,
                 env_file: str | None, sql_dir: str | None) -> None:
    """Revoke and drop the demo role.

    Runs sql/cleanup_role.sql with admin_role to revoke the demo role
    from the user and drop it. Run this AFTER scc-cleanup.
    """
    env = _require_env(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME",
        "SNOWFLAKE_USER",
        env_file=env_file,
    )
    _run_snow_sql(
        "cleanup_role.sql",
        variables={
            "admin_role": admin_role,
            "demo_role": demo_role,
            "snowflake_user": env["SNOWFLAKE_USER"],
        },
        connection=env["SNOWFLAKE_DEFAULT_CONNECTION_NAME"],
        dry_run=dry_run,
        sql_dir=sql_dir,
    )
