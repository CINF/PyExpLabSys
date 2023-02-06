
"""This module defines tasks for the tool runner `invoke`"""

from pathlib import Path
from shutil import rmtree, which
from invoke import task
try:
    from rich import print as rprint
except ImportError:
    rprint = print

THIS_DIR = Path(__file__).parent


@task(aliases=["bd"])
def build_docs(context):
    """Build the (html) documentation"""
    with context.cd(THIS_DIR / "doc"):
        context.run("sphinx-build -b html -d build/doctrees source build/html")
    print("The freshly built docs can be opened with `invoke open-docs`")


@task(aliases=["od"])
def open_docs(context):
    """Open the docs and builds them first if necessary"""
    if which("xdg-open") is None:
        print(
            "Cannot open docs without the `xdg-open` command. This likely "
            "means you are on Windows, and a suitable alternative will have "
            "to be implemented in `tasks.py` for Windows support"
        )
        return

    index_path = THIS_DIR / "doc" / "build" / "html" / "index.html"
    if not index_path.is_file():
        build_docs(context)
    with context.cd(THIS_DIR):
        context.run(f"xdg-open {index_path}")

        
CLEAN_PATTERNS = ("__pycache__", "*.pyc", "*.pyo", ".mypy_cache", "build")


@task(
    help={
        "dryrun": (
            "Only display the files and folders that would be deleted by the "
            "cleanup, but do not actually delete them"
        ),
    },
)
def clean(context, dryrun=False):
    """Clean the repository

    Will remove all files and folders that contains the following patterns:
    => {}
    """
    if dryrun:
        print("CLEANING DRYRUN")
    for clean_pattern in CLEAN_PATTERNS:
        for cleanpath in THIS_DIR.glob("**/" + clean_pattern):
            # Ignore stuff in .venv
            if ".venv" in cleanpath.parts:
                continue

            if cleanpath.is_dir():
                print("DELETE DIR :", cleanpath)
                if not dryrun:
                    rmtree(cleanpath)
            else:
                print("DELETE FILE:", cleanpath)
                if not dryrun:
                    cleanpath.unlink()


clean.__doc__ = clean.__doc__.format(", ".join(CLEAN_PATTERNS))


@task(aliases=["pylint", "l"])
def lint(context):
    """Run linting tool on all of PyExpLabSys"""
    with context.cd(THIS_DIR):
        result = context.run("pylint PyExpLabSys")
        if result.return_code == 0:
            rprint("[bold green]Files linted. No errors.")
    return result.return_code


@task(aliases=["pytest", "t"])
def test(context):
    """Run non-equipment dependent tests"""
    with context.cd(THIS_DIR):
        result = context.run("pytest --color yes tests/unittests/ tests/functional_test/")
        if result.return_code == 0:
            rprint("[bold green]All tests passed")
    return result.return_code


@task(aliases=["deps", "d"])
def dependencies(context):
    """Install normal and development dependencies"""
    context.run("python -m pip install --upgrade pip")
    context.run("pip install --upgrade -r requirements.txt")
    context.run("pip install --upgrade -r requirements-dev.txt")


@task(aliases=["black", "f", "b"])
def format(context):
    """Run all source code through the code formatter"""
    with context.cd(THIS_DIR):
        context.run("black PyExpLabSys")

@task(aliases=["check_black", "cf", "cb"])
def check_format(context):
    """Check that the code has already been run through the code formatter"""
    with context.cd(THIS_DIR):
        result = context.run("black --check PyExpLabSys")
        if result.return_code == 0:
            rprint("[bold green]Code format checked. No issues.")
    return result.return_code

@task(aliases=["check", "c"])
def checks(context):
    """Check the code with flake8 and mypy"""
    combined_return_code = check_format(context)
    combined_return_code += lint(context)
    combined_return_code += test(context)
    if combined_return_code == 0:
        print()
        print(r"+----------+")
        print(r"| All good |")
        print(r"+----------+")