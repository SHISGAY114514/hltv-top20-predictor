"""Single current-model entry point."""
import argparse
import sys
from .pipeline import build, load, prepare
from .aggregate import score, validate

def main(argv=None):
    parser = argparse.ArgumentParser(description="HTPM 4.3 · 双 Major 年度预测")
    parser.add_argument("command", choices=("build", "validate", "refresh", "replay"))
    parser.add_argument("--model", choices=("4.4","4.3","4.2","4.1.1"), default="4.3")
    parser.add_argument("--input", help="双 Major 赛后数据包目录")
    args = parser.parse_args(argv)
    if args.model == "4.4" and (args.input or args.command not in ("build", "validate")):
        parser.error("4.4 uses the frozen 2026-11-17 snapshot for build and validate")
    try:
        if args.command == "replay":
            if args.model == "4.1.1" or args.input:
                parser.error("replay uses the fixed 2025 archive for 4.2/4.3")
            if args.model=="4.3":
                from .forecast_4_3 import replay
            else:
                from .forecast_4_2 import replay
            print(replay())
        elif args.command in ("build","validate","refresh") and args.model in ("4.2","4.3","4.4"):
            from .forecast_4_2 import calculate, publish, refresh, STATES
            result = refresh(args.input,model=args.model) if args.command=="refresh" else calculate(args.input,model=args.model)
            print(STATES[result["state"]], result["cutoff"], publish(result, verify=args.command=="validate"))
        elif args.input or args.command=="refresh":
            parser.error("--input applies only to 4.2/4.3 build, validate or refresh")
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
