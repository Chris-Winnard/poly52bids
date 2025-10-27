import os
import shutil
import pathlib

"""Where there are two BIDS datasets and you want to mass-move files from one to the other
(designed for when an updated version of the bids dataset folder was created but the older
 version already had tidied beh files, so it was more convenient to transfer from the former
 to the latter)"""

# Define source and destination base directories
currentFolderPath = pathlib.Path(__file__).parent.resolve()
basePath =  str(currentFolderPath.parent.resolve()) + "\\"

src_base = basePath + "bids_dataset"
dst_base = basePath + "bids_dataset_OG"

# Walk through the source directory
for root, _, files in os.walk(src_base):
    for file in files:
        if file.endswith("_eeg.json"):
            # Full path of the source file
            src_file = os.path.join(root, file)

            # Construct the corresponding destination path
            relative_path = os.path.relpath(src_file, src_base)
            dst_file = os.path.join(dst_base, relative_path)

            # Ensure destination folder exists
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)

            # Copy the file
            shutil.copy2(src_file, dst_file)
            print(f"Copied: {src_file} -> {dst_file}")
