"""Run teamengine and parse results."""

import logging
import typing
from pathlib import Path

import click
import httpx
import typer
from rich import print
from rich import print_json

from . import teamengine_runner

logger = logging.getLogger(__name__)
app = typer.Typer()


@app.callback()
def base_callback(
    ctx: typer.Context,
    debug: bool = False,
    network_timeout: int = 20
) -> None:
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    ctx_obj = ctx.ensure_object(dict)
    ctx_obj.update({
        "debug": debug,
        "network_timeout": network_timeout,
    })
    ctx_obj["debug"] = debug


@app.command()
def execute_test_suite(
    ctx: typer.Context,
    teamengine_base_url: str,
    test_suite_identifier: str,
    test_suite_input: typing.Annotated[
        typing.Optional[list[click.Tuple]],
        typer.Option(click_type=click.Tuple([str, str]))
    ] = None,
    persist_response: typing.Optional[Path] = None
):
    logger.debug(f"{locals()=}")
    client = httpx.Client(timeout=ctx.obj["network_timeout"])
    base_url = teamengine_base_url.strip("/")
    teamengine_available = teamengine_runner.wait_for_teamengine_to_be_ready(
        client, base_url)
    if teamengine_available:
        suite_args = {}
        for arg_name, arg_value in (test_suite_input or []):
            values = suite_args.setdefault(arg_name, [])
            values.append(arg_value)
        logger.debug(
            f"Asking teamengine to execute test suite {test_suite_identifier!r}...")
        raw_result = teamengine_runner.execute_test_suite(
            client,
            base_url,
            test_suite_identifier,
            test_suite_arguments=suite_args,
            teamengine_username="ogctest",
            teamengine_password="ogctest",
        )
        logger.debug(f"Test suite is done executing")
        if raw_result:
            if persist_response is not None:
                persist_response.write_text(raw_result)
                logger.debug(f"Wrote raw response to {persist_response!r}")
            logger.debug(f"Parsing test suite execution results...")
            test_summary = teamengine_runner.parse_test_results(raw_result)
            print_json(data=test_summary)
        else:
            logger.critical(f"Unable to collect test suite execution results")
            raise SystemExit(1)
    else:
        logger.critical(f"teamengine service is not available")
        raise SystemExit(1)


