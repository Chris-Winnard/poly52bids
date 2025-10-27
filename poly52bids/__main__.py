# __main__.py

import argparse
from poly52bids_fullConv import *
import pathlib

"See poly52bids_fullConv.py for an explanation of the workflow."

def parse_subjects(subject_inputs):
    subjects = set()
    for item in subject_inputs:
        item = item.strip().lower()
        if item == "all":
            subjects.update(range(1, 33))
        elif "-" in item:
            try:
                start, end = map(int, item.split("-"))
                if start > end:
                    raise ValueError
                subjects.update(range(start, end + 1))
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid range: {item}")
        else:
            try:
                subjects.add(int(item))
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid subject: {item}")
    return sorted(subjects)

def none_or_str(value):
    """Convert a string to None if it equals 'none', otherwise return the value. This is case-insensitive and ignores whitespace, e.g., " nOnE " -> None)"""
    if isinstance(value, str) and value.strip().lower() == "none":
        return None    
    else:
        return value.strip().lower()

def main():
    parser = argparse.ArgumentParser(description="Convert data from .poly5 eeg + .csv behavioural files to BIDS format")
    parser.add_argument("--basePath", type=str, required=False,
                        help="Base path of the project, where sourcedata is expected to be found and bids_dataset will be saved"
                        + " (default: parent of this package)")
    parser.add_argument("--eeglabPath", type=str, required=False,
                        help="Path to EEGLAB (default: 'eeglab' folder inside input_dir)")
    parser.add_argument("--subjects", type=str, nargs='+', required=True,
                        help="Subject list (e.g., 'all', '1-5', '8 10 12-14')")
    parser.add_argument("--processExtraData", type=none_or_str, choices=["exclusively", "additionally", "none"], default="additionally",
                        help="Whether to process extra data only, additionally, or not at all")
    parser.add_argument("--filterBufferPeriod", type=int, default=7,
                        help="Filter buffer period in seconds")
    parser.add_argument("--sourcedataTransfer", type=none_or_str, choices=["copy", "move", "none"], default="none",
                        help="Whether to copy sourcedata to the final bids_dataset directory, move it (removing the original), or do neither.")
    args = parser.parse_args()

    # Resolve base path
    if args.basePath:
        basePath = pathlib.Path(args.basePath).resolve()
    else:
        basePath = pathlib.Path(__file__).parent.parent.resolve()

    eeglabPath = args.eeglabPath or str(basePath / "eeglab")
    subject_list = parse_subjects(args.subjects)
    
    poly52bids_fullConv(subjects=[f"{s:02d}" for s in subject_list],
                        filterBufferPeriod=args.filterBufferPeriod,
                        basePath=str(basePath),
                        eeglabPath=str(eeglabPath),
                        processExtraData=args.processExtraData,
                        sourcedataTransfer=args.sourcedataTransfer)

if __name__ == "__main__":
    main()