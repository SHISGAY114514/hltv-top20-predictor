"""Single current-model entry point."""
import argparse
import sys
from .pipeline import build, load, prepare
from .aggregate import score, validate

def main(argv=None):
    parser = argparse.ArgumentParser(description="HTPM 4.1.1: tier and stage season forecast")
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build()
        else:
            data, config, _ = prepare()
            validate(data, config)
            from .season_forecast import run
            base = score(data, config)
            if base != load("output/current/scores.json") or run(base,write=False) != load("output/forecast_4_1_1/scores.json"):
                raise ValueError("Forecast differs from saved result; run build")
            print("Validated 3.5 reference and all 4.1.1 rankings")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("Error: " + str(error), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
