"""A small command-line example to build on."""

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JAW starter application.")
    parser.add_argument("--name", default="world", help="Name to greet")
    args = parser.parse_args(argv)
    print(f"Hello, {args.name}!")
    return 0
