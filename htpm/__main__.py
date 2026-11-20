"""Single current-model entry point."""
import argparse
import sys
from .pipeline import build, load, prepare
from .aggregate import score, validate

def main(argv=None):
    parser = argparse.ArgumentParser(description="HTPM 4.2 · 双 Major 年度预测")
    parser.add_argument("command", choices=("build", "validate", "refresh", "replay"))
    parser.add_argument("--model", choices=("4.2","4.1.1"), default="4.2")
    parser.add_argument("--input", help="4.2 赛后数据包目录")
    args = parser.parse_args(argv)
    try:
        if args.command == "replay":
            if args.model != "4.2" or args.input:
                parser.error("replay uses the fixed 2025 archive for 4.2")
            from .forecast_4_2 import replay
            print(replay())
        elif args.command in ("build","validate","refresh") and args.model == "4.2":
            from .forecast_4_2 import calculate, publish, refresh, STATES
            result = refresh(args.input) if args.command=="refresh" else calculate(args.input)
            print(STATES[result["state"]], result["cutoff"], publish(result, verify=args.command=="validate"))
        elif args.input or args.command=="refresh":
            parser.error("--input applies only to 4.2 build/validate")
        elif args.command == "build":
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
